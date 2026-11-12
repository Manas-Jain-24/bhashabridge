"""Start a mock-model API against a disposable database, never a learner database."""
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    with tempfile.TemporaryDirectory(prefix='bhashabridge-e2e-') as directory:
        os.environ.update(DATABASE_URL='sqlite:///'+(Path(directory)/'e2e.db').as_posix(),
            APP_ENV='test',AUTH_MODE='accounts',COOKIE_SECURE='false',TESTING='false',
            USE_MOCK_MODELS='true',GEMINI_API_KEY='',HF_TOKEN='',ALLOW_REGISTRATION='true',
            REQUESTS_PER_MINUTE='1000',CLOUD_CALLS_PER_DAY='0',INIT_DB_ON_STARTUP='true')
        import uvicorn
        uvicorn.run('app.main:app',host='127.0.0.1',port=18082,log_level='warning')


if __name__=='__main__':main()
