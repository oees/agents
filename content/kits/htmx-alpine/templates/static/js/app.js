/*
 * Page wiring for htmx and Alpine under a strict CSP.
 *
 * base.html loads htmx, then this file, then Alpine, all with `defer`, so this
 * runs after htmx is defined and before either library initialises the page.
 * UI state only: data rules and business logic stay on the server.
 */
(function () {
  "use strict";

  // htmx: nothing that needs eval, inline <script> or an injected <style>.
  Object.assign(htmx.config, {
    allowEval: false,
    allowScriptTags: false,
    includeIndicatorStyles: false,
    inlineScriptNonce: "",
    inlineStyleNonce: "",
    selfRequestsOnly: true,
    // Swapped screens can hold customer data: keep no copies in sessionStorage
    // and reload the real page on back/forward instead.
    historyCacheSize: 0,
    refreshOnHistoryMiss: true,
    historyRestoreAsHxRequest: false,
    // 422 carries the re-rendered form with its errors, so it is swapped too.
    responseHandling: [
      { code: "204", swap: false },
      { code: "[23]..", swap: true },
      { code: "422", swap: true },
      { code: "[45]..", swap: false, error: true },
    ],
  });

  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const liveRegion = document.getElementById("live-region");

  function announce(text) {
    if (!liveRegion || !text) {
      return;
    }
    // Clear first so the same text is announced again.
    liveRegion.textContent = "";
    window.setTimeout(function () {
      liveRegion.textContent = text;
    }, 50);
  }

  function setBusy(element, busy) {
    if (!(element instanceof Element)) {
      return;
    }
    if (busy) {
      element.setAttribute("aria-busy", "true");
    } else {
      element.removeAttribute("aria-busy");
    }
  }

  // Focus the first invalid field, else an element the partial marked with
  // data-focus-after-swap (the h1 of a screen reached by navigation), and
  // announce any data-announce text the partial carries.
  function afterSwap(root) {
    if (!(root instanceof Element)) {
      return;
    }
    const invalid = root.querySelector('[aria-invalid="true"]');
    const marked = root.matches("[data-focus-after-swap]")
      ? root
      : root.querySelector("[data-focus-after-swap]");
    const focusTarget = invalid || marked;
    if (focusTarget) {
      if (focusTarget === marked && !focusTarget.hasAttribute("tabindex")) {
        focusTarget.setAttribute("tabindex", "-1");
      }
      focusTarget.focus();
    }
    const announcer = root.matches("[data-announce]") ? root : root.querySelector("[data-announce]");
    if (announcer) {
      announce(announcer.getAttribute("data-announce"));
    }
  }

  function reportFailure(kind, detail) {
    const xhr = detail.xhr;
    console.error({
      event: kind,
      path: detail.pathInfo ? detail.pathInfo.requestPath : null,
      status: xhr ? xhr.status : null,
      request_id: xhr ? xhr.getResponseHeader("X-Request-ID") : null,
    });
    announce(liveRegion ? liveRegion.getAttribute("data-error-message") : "");
  }

  document.addEventListener("htmx:configRequest", function (event) {
    if (csrfMeta && event.detail.verb !== "get") {
      event.detail.headers["X-CSRFToken"] = csrfMeta.getAttribute("content");
    }
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    setBusy(event.detail.target, true);
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    setBusy(event.detail.target, false);
  });

  document.addEventListener("htmx:afterSettle", function (event) {
    afterSwap(event.target);
  });

  document.addEventListener("htmx:responseError", function (event) {
    reportFailure("htmx_response_error", event.detail);
  });

  document.addEventListener("htmx:sendError", function (event) {
    reportFailure("htmx_send_error", event.detail);
  });

  // Alpine components: register each with Alpine.data() and reference it by
  // name (x-data="disclosure"). The CSP build cannot evaluate inline objects.
  document.addEventListener("alpine:init", function () {
    Alpine.data("disclosure", function () {
      return {
        open: false,
        toggle() {
          this.open = !this.open;
        },
        close() {
          this.open = false;
        },
      };
    });
  });
})();
