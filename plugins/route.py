# Don't Remove Credit @Linux_Bots

import math
import logging
import mimetypes
import secrets

from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine

from info import *
from TechVJ.bot import multi_clients, work_loads
from TechVJ.server.exceptions import FIleNotFound, InvalidHash
from TechVJ.util.custom_dl import ByteStreamer
from TechVJ.util.render_template import render_page

routes = web.RouteTableDef()

# CACHE
class_cache = {}


# =========================================================
# ROOT
# =========================================================

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(
        text="Bot Running Successfully"
    )


# =========================================================
# WATCH PAGE
# =========================================================

@routes.get(r"/watch/{file_id:\d+}/{file_name:.+}", allow_head=True)
async def watch_handler(request: web.Request):

    try:
        print("WATCH HIT:", request.path)

        file_id = int(request.match_info["file_id"])

        secure_hash = request.rel_url.query.get("hash")

        if not secure_hash:
            return web.Response(
                text="Missing hash",
                status=400
            )

        html = await render_page(
            file_id,
            secure_hash
        )

        return web.Response(
            text=html,
            content_type="text/html"
        )

    except InvalidHash:
        return web.Response(
            text="Invalid hash",
            status=403
        )

    except FIleNotFound:
        return web.Response(
            text="File not found",
            status=404
        )

    except (
        AttributeError,
        BadStatusLine,
        ConnectionResetError
    ):
        return web.Response(
            text="Invalid request",
            status=400
        )

    except Exception as e:
        logging.exception(e)

        return web.Response(
            text="Internal Server Error",
            status=500
        )


# =========================================================
# FILE STREAM
# =========================================================

@routes.get(r"/{file_id:\d+}/{file_name:.+}", allow_head=True)
async def file_stream_handler(request: web.Request):

    try:
        print("STREAM HIT:", request.path)

        file_id = int(request.match_info["file_id"])

        secure_hash = request.rel_url.query.get("hash")

        if not secure_hash:
            return web.Response(
                text="Missing hash",
                status=400
            )

        return await media_streamer(
            request,
            file_id,
            secure_hash
        )

    except InvalidHash:
        return web.Response(
            text="Invalid hash",
            status=403
        )

    except FIleNotFound:
        return web.Response(
            text="File not found",
            status=404
        )

    except (
        AttributeError,
        BadStatusLine,
        ConnectionResetError
    ):
        return web.Response(
            text="Invalid request",
            status=400
        )

    except Exception as e:
        logging.exception(e)

        return web.Response(
            text="Internal Server Error",
            status=500
        )


# =========================================================
# MEDIA STREAMER
# =========================================================

async def media_streamer(
    request: web.Request,
    file_id: int,
    secure_hash: str
):

    range_header = request.headers.get("Range")

    # FASTEST CLIENT
    index = min(
        work_loads,
        key=work_loads.get
    )

    faster_client = multi_clients[index]

    # CACHE
    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]

    else:
        tg_connect = ByteStreamer(faster_client)

        class_cache[faster_client] = tg_connect

    # GET FILE
    file = await tg_connect.get_file_properties(file_id)

    # DEBUG
    print("FILE UNIQUE ID:", file.unique_id)
    print("HASH FROM URL:", secure_hash)

    # HASH CHECK
    if file.unique_id[:6] != secure_hash:
        raise InvalidHash

    file_size = file.file_size

    # RANGE SUPPORT
    if range_header:

        from_bytes, until_bytes = range_header.replace(
            "bytes=",
            ""
        ).split("-")

        from_bytes = int(from_bytes)

        until_bytes = (
            int(until_bytes)
            if until_bytes
            else file_size - 1
        )

    else:

        from_bytes = 0
        until_bytes = file_size - 1

    # INVALID RANGE
    if (
        from_bytes < 0
        or until_bytes >= file_size
        or from_bytes > until_bytes
    ):

        return web.Response(
            status=416,
            text="Requested Range Not Satisfiable",
            headers={
                "Content-Range": f"bytes */{file_size}"
            }
        )

    chunk_size = 1024 * 1024

    offset = from_bytes - (
        from_bytes % chunk_size
    )

    first_part_cut = from_bytes - offset

    last_part_cut = (
        until_bytes % chunk_size
    ) + 1

    req_length = (
        until_bytes - from_bytes
    ) + 1

    part_count = (
        math.ceil(until_bytes / chunk_size)
        - math.floor(offset / chunk_size)
    )

    body = tg_connect.yield_file(
        file,
        index,
        offset,
        first_part_cut,
        last_part_cut,
        part_count,
        chunk_size
    )

    mime_type = (
        file.mime_type
        or mimetypes.guess_type(
            file.file_name
        )[0]
        or "application/octet-stream"
    )

    file_name = (
        file.file_name
        or f"{secrets.token_hex(5)}"
    )

    return web.Response(

        status=206 if range_header else 200,

        body=body,

        headers={

            "Content-Type": mime_type,

            "Accept-Ranges": "bytes",

            "Content-Length": str(req_length),

            "Content-Range": (
                f"bytes {from_bytes}-{until_bytes}/{file_size}"
            ),

            "Content-Disposition": (
                f'inline; filename="{file_name}"'
            ),
        },
    )
