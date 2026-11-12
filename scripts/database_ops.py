"""SQLite backup/restore drills; restores always create a new database file."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def copy_database(source, destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if not source.is_file(): raise ValueError('Source database does not exist')
    if destination.exists() or source==destination:
        raise ValueError('Destination must be a new file; an existing database is never overwritten')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # SQLite backup includes committed WAL contents consistently while a server runs.
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as original:
        with closing(sqlite3.connect(destination)) as copied:
            original.backup(copied)
            if copied.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Copied database failed integrity validation')
            tables=[row[0] for row in copied.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            counts={name:copied.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in tables}
    return {'integrity':'ok','table_counts':counts,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore','drill'])
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    result=copy_database(args.source,args.destination)
    result['action']=args.action
    # The manifest contains counts/hashes only, never rows or authentication data.
    args.destination.with_suffix(args.destination.suffix+'.manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
