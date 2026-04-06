from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from thohago.web.dependencies import get_runtime
from thohago.web.runtime import WebRuntime


router = APIRouter()


@router.get("/manifest.webmanifest")
def manifest(runtime: WebRuntime = Depends(get_runtime)) -> JSONResponse:
    payload = {
        "name": "Thohago",
        "short_name": "Thohago",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f7f4ec",
        "theme_color": "#6d4e21",
        "description": "Thohago mobile intake and preview shell.",
    }
    return JSONResponse(payload, media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker() -> Response:
    script = """
const CACHE_NAME = "thohago-shell-v1";
const OFFLINE_URL = "/offline";
const ASSETS = [OFFLINE_URL, "/manifest.webmanifest", "/static/app.css"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
""".strip()
    return Response(content=script, media_type="application/javascript")


@router.get("/offline", response_class=HTMLResponse)
def offline_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
) -> HTMLResponse:
    return runtime.templates.TemplateResponse(
        request,
        "offline.html",
        {
            "title": "Offline",
        },
    )
