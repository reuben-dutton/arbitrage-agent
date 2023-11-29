import asyncio
from httpx import Response


def construct_delayed_response(delay, status=200):

    async def delayed_response(request):
        await asyncio.sleep(delay)
        return Response(status)

    return delayed_response
