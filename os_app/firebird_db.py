# os_app/firebird_db.py
import fdb
from contextlib import contextmanager
from django.conf import settings

FB_CFG = getattr(settings, "FIREBIRD_DB", None)
if not FB_CFG:
    raise RuntimeError("Configure FIREBIRD_DB em settings.py (dsn/user/password/charset).")

CHARSET = FB_CFG.get("charset", "ISO8859_1")

@contextmanager
def fb_connect():
    con = fdb.connect(
        dsn=FB_CFG['dsn'],
        user=FB_CFG['user'],
        password=FB_CFG['password'],
        charset=CHARSET,
    )
    try:
        yield con
    finally:
        try:
            con.close()
        except Exception:
            pass
