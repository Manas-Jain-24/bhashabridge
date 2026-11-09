"""Keep training outputs inside a project and metadata paths portable."""
from pathlib import Path


def experiment_directory(value,root):
    root=Path(root).resolve(); directory=Path(value).resolve()
    if not directory.is_relative_to(root): raise ValueError('Experiment output must be inside the project')
    return directory


def save_epoch(model,directory,epoch,root):
    directory=experiment_directory(directory,root)
    checkpoint=directory/f'epoch-{epoch}'
    model.save_pretrained(checkpoint,safe_serialization=True)
    return checkpoint.relative_to(Path(root).resolve()).as_posix()
