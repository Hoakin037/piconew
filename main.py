from socketio import ASGIApp

from app.common.core.app_config import app_fabric
from app.common.core.sio import sio
from app.modules.messages import routes  # noqa: F401

app = app_fabric()
app = ASGIApp(sio, app)
