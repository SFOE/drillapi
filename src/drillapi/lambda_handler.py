from .app import app
from mangum import Mangum   

# Lambda entrypoint
handler = Mangum(app)