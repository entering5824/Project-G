import io
import json
import hashlib
import os
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from projectg.application.backups.errors import BackupError
from projectg.infrastructure.backups.local_backup_gateway import LocalBackupGateway
from projectg.infrastructure.persistence.sqlite.base import Base
from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator


def make_service(tmp_path):
    database=tmp_path/'app.db'
    engine=create_engine(f'sqlite:///{database}')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Account(id='main',name='Main',server_region='ASIA',current_snapshot_id='snap-1'))
        db.add(Snapshot(id='snap-1',account_id='main',good_format='GOOD',good_version=1,good_db_version=60,
            raw_file_hash='rawhash',canonical_state_hash='statehash',previous_snapshot_id=None,
            importer_version='test',raw_path=str(tmp_path/'snapshots'/'good.json')))
        db.commit()
    snapshots=tmp_path/'snapshots';snapshots.mkdir()
    (snapshots/'good.json').write_text('{"format":"GOOD"}',encoding='utf-8')
    configuration = Settings(
        database_url=f'sqlite:///{database.as_posix()}', snapshot_dir=snapshots,
        backup_dir=tmp_path/'backups', akasha_dir=tmp_path/'akasha')
    service=LocalBackupGateway(configuration=configuration, clock=SystemClock(),
                               id_generator=Uuid4IdGenerator())
    return service,database,engine,snapshots


def test_backup_export_restore_manifest_snapshot_paths_and_pre_restore_copy(tmp_path):
    service,database,engine,snapshots=make_service(tmp_path)
    result=service.create_manual(str(tmp_path/"backups"/"manual.zip"))
    backup=__import__("pathlib").Path(result.path); manifest=result.manifest.to_mapping()
    assert backup.is_file()
    assert manifest['backupSchemaVersion']==2
    with zipfile.ZipFile(backup) as archive:
        assert {'manifest.json','settings.json','database.sqlite','snapshots/good.json','akasha/'}<=set(archive.namelist())
        exported=json.loads(archive.read('manifest.json'))
        assert exported['snapshotFileCount']==1 and exported['includesAkashaImages'] is False

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE accounts SET name='Changed'")
    result=service.restore_content(backup.read_bytes())
    assert result.manifest.backup_schema_version==2
    assert __import__('pathlib').Path(result.pre_restore_backup).is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT name FROM accounts WHERE id=?',('main',)).fetchone()[0]=='Main'
        raw_path=connection.execute('SELECT raw_path FROM snapshots WHERE id=?',('snap-1',)).fetchone()[0]
    assert __import__('pathlib').Path(raw_path).read_text(encoding='utf-8')=='{"format":"GOOD"}'
    engine.dispose()


def test_automatic_backup_rolling_retention_keeps_manual_exports(tmp_path):
    service,database,engine,_=make_service(tmp_path)
    manual_result=service.create_manual(str(tmp_path/"backups"/"manual.zip"))
    manual=__import__("pathlib").Path(manual_result.path)
    for _ in range(3):
        service.create_automatic_backup("PRE_TARGET_CHANGE",keep_last=2)
    rolling=list((tmp_path/"backups").glob("auto_*.zip"))
    assert len(rolling)==2
    assert manual.is_file()
    engine.dispose()


def test_automatic_backup_retention_keeps_recent_daily_and_weekly_union(tmp_path):
    service,_,engine,_=make_service(tmp_path)
    service.backup_dir.mkdir(parents=True, exist_ok=True)
    anchor = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
    files = []
    for age in range(40):
        path = service.backup_dir / f"auto_{age:02d}_TEST.zip"
        path.write_bytes(b"backup")
        created = (anchor - timedelta(days=age)).timestamp()
        os.utime(path, (created, created))
        files.append(path)
    manual = service.backup_dir / "backup_manual.zip"
    manual.write_bytes(b"manual")
    weekly = {}
    for path in files:
        created = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        iso = created.isocalendar()
        weekly.setdefault((iso.year, iso.week), path)

    service._prune_automatic_backups()

    retained = set(service.backup_dir.glob("auto_*.zip"))
    assert set(files[:20]) <= retained
    assert set(list(weekly.values())[:4]) <= retained
    assert manual.is_file()
    assert not files[-1].exists()
    engine.dispose()


def test_corrupt_or_incompatible_backup_is_rejected_without_touching_database(tmp_path):
    service,database,engine, _=make_service(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE accounts SET name='Keep me'")
    with pytest.raises(BackupError,match='valid ZIP'):
        service.restore_content(b'not a zip')
    backup_result=service.create_manual(str(tmp_path/"backups"/"manual.zip"))
    backup=__import__("pathlib").Path(backup_result.path)
    output=io.BytesIO()
    with zipfile.ZipFile(backup) as source, zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename=='manifest.json':
                manifest=json.loads(data);manifest['databaseSchemaVersion']='9999_future'
                data=json.dumps(manifest).encode()
            target.writestr(item.filename,data)
    with pytest.raises(BackupError,match='not supported'):
        service.restore_content(output.getvalue())
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT name FROM accounts WHERE id=?',('main',)).fetchone()[0]=='Keep me'
    engine.dispose()


def test_restore_corrupt_database_keeps_current_state_and_recovery_zip(tmp_path):
    service,database,engine,_=make_service(tmp_path)
    backup_result=service.create_manual(str(tmp_path/"backups"/"manual.zip"))
    backup=__import__("pathlib").Path(backup_result.path)
    output=io.BytesIO()
    with zipfile.ZipFile(backup) as source:
        files={item.filename:source.read(item.filename) for item in source.infolist()}
    files['database.sqlite']=b'not sqlite'
    manifest=json.loads(files['manifest.json'])
    manifest['files']['database.sqlite']={
        'sha256':hashlib.sha256(files['database.sqlite']).hexdigest(),
        'sizeBytes':len(files['database.sqlite']),
    }
    files['manifest.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as target:
        for name,data in files.items():
            target.writestr(name,data)
    with pytest.raises(BackupError): service.restore_content(output.getvalue())
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT name FROM accounts WHERE id=?',('main',)).fetchone()[0]=='Main'
    assert list((tmp_path/'backups').glob('pre_restore_*.zip'))
    engine.dispose()
