from aiohttp import web

heartbeat = web.get('/heartbeat', lambda request: web.Response())
