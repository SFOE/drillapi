from mangum import Mangum

from .app import app

# Lambda entrypoint
handler = Mangum(app)
