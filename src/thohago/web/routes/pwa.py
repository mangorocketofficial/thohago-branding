from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from thohago.web.dependencies import get_runtime
from thohago.web.runtime import WebRuntime


router = APIRouter()


@router.get("/manifest.webmanifest")
def manifest(runtime: WebRuntime = Depends(get_runtime)) -> JSONResponse:
    payload = {
        "name": "또하고 모바일",
        "short_name": "또하고",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f7f4ec",
        "theme_color": "#6d4e21",
        "description": "모바일에서 업로드와 인터뷰를 진행하는 또하고 웹앱",
    }
    return JSONResponse(payload, media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker() -> Response:
    script = """
const CACHE_NAME = "thohago-shell-v2";
const OFFLINE_URL = "/offline";
const ASSETS = [OFFLINE_URL, "/manifest.webmanifest", "/static/app.css"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("thohago-shell-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname === "/static/app.css") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
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
            "title": "오프라인",
        },
    )
