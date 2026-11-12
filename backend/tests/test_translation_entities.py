import pytest


@pytest.fixture
def processor():
    pytest.importorskip('indicnlp')
    from app.services.translation.indic_processor import IndicScriptProcessor
    return IndicScriptProcessor()


def roundtrip(processor, texts):
    prepared=processor.preprocess_batch(texts,'hin_Deva','mar_Deva')
    return processor.postprocess_batch([text.split(' ',2)[2] for text in prepared],'hin_Deva')


def test_entities_restore_exactly_without_cross_sentence_contamination(processor):
    inputs=['यह https://example.org/a?q=12 और a+b@example.org है।',
            'राशि 1,250.50 है और दिनांक 12/08/2026 है।']
    outputs=roundtrip(processor,inputs)
    for expected in ('https://example.org/a?q=12','a+b@example.org'): assert expected in outputs[0]
    for expected in ('1,250.50','12/08/2026'): assert expected in outputs[1]
    assert 'example.org' not in outputs[1]


def test_bare_domain_and_quoted_link_are_preserved(processor):
    result=roundtrip(processor,['यह example.org/help और "https://example.org/news" है।'])[0]
    assert 'example.org/help' in result and '"https://example.org/news"' in result


def test_failed_generation_maps_are_replaced_by_next_request(processor):
    processor.preprocess_batch(['https://old.example.org'],'hin_Deva','mar_Deva')
    assert 'https://new.example.org' in roundtrip(processor,['https://new.example.org'])[0]
    assert not processor._entity_maps


def test_training_targets_have_no_language_tags_or_entity_masks():
    pytest.importorskip('indicnlp')
    from app.services.translation.indic_processor import IndicScriptProcessor
    processor=IndicScriptProcessor(inference=False)
    target=processor.preprocess_batch(['रक्कम १२,५०० आहे।'],'mar_Deva','ben_Beng',is_target=True)[0]
    assert not target.startswith('mar_Deva') and '<ID' not in target
    assert '12' in target


def test_literal_marker_does_not_collide_with_generated_markers(processor):
    result=roundtrip(processor,['यह <ID1> और https://example.org है।'])[0]
    assert '<ID1>' in result and 'https://example.org' in result


def test_dropped_entity_is_an_error_instead_of_silent_data_loss(processor):
    from app.services.translation.indic_processor import EntityPreservationError
    processor.preprocess_batch(['पता help@example.org है।'],'hin_Deva','mar_Deva')
    with pytest.raises(EntityPreservationError): processor.postprocess_batch(['पत्ता आहे।'],'mar_Deva')


def test_vernacular_marker_is_restored_before_bengali_script_conversion(processor):
    processor.preprocess_batch(['पता help@example.org है।'],'hin_Deva','ben_Beng')
    assert 'help@example.org' in processor.postprocess_batch(['पत्ता <आईडी1> आहे।'],'ben_Beng')[0]


@pytest.mark.parametrize('marker',['< आइडि1 >','< आई डि 1 >','< आयडी1 >','< ID1 >'])
def test_model_marker_spellings_restore_identifiers_across_scripts(processor,marker):
    processor.preprocess_batch(['पता https://example.org/Guide है।'],'hin_Deva','ben_Beng')
    assert 'https://example.org/Guide' in processor.postprocess_batch(['ठिकाना '+marker+' ।'],'ben_Beng')[0]


@pytest.mark.parametrize('value',['.5','-.25','-3','+8','07:35','12.5','30%','1234'])
def test_numeric_signs_precision_and_format_survive_all_target_scripts(processor,value):
    for target in ('hin_Deva','mar_Deva','ben_Beng'):
        prepared=processor.preprocess_batch(['मूल्य '+value+' है।'],'hin_Deva',target)
        assert processor._entity_maps==[{1:value}]
        assert value in processor.postprocess_batch([prepared[0].split(' ',2)[2]],target)[0]


def test_duplicate_entity_marker_is_rejected(processor):
    from app.services.translation.indic_processor import EntityPreservationError
    processor.preprocess_batch(['राशि +8 है।'],'hin_Deva','mar_Deva')
    with pytest.raises(EntityPreservationError):
        processor.postprocess_batch(['रक्कम <ID1> <ID1> आहे।'],'mar_Deva')


def test_unknown_placeholders_and_corrupted_marker_runs_are_rejected():
    from app.services.translation.generation import validate_native_output,OutputArtifactError
    for text in ('मूल्य < ID3 > है।','टोंगामध्ये ω09 ω0 ω2 ω1।'):
        with pytest.raises(OutputArtifactError): validate_native_output(text)
    assert validate_native_output('The equation uses ω1 and ω2.')
    assert validate_native_output('यह <ID1> है।','यह <ID1> है।')


@pytest.mark.parametrize('language,text',[('hindi','कल https://example.org/team पर पढ़िए।'),
                                         ('bengali','আজ help@example.org দেখুন।')])
def test_transliteration_does_not_corrupt_entities_before_translation(language,text):
    from app.services.transliteration.service import transliteration_service
    for direction in ('latin_to_native','native_to_latin'):
        result=transliteration_service.transliterate(text,language,direction)
        entity='https://example.org/team' if language=='hindi' else 'help@example.org'
        assert entity in result
