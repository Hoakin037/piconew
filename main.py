from socketio import ASGIApp

from app.common.core.app_config import app_fabric
from app.common.core.sio import sio

app = app_fabric()
app = ASGIApp(sio, app)
