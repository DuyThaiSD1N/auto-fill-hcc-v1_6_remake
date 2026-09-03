//#region node_modules/.pnpm/scanic@1.6.0/node_modules/scanic/dist/scanic-mlDetector.js
var e = [
	.485,
	.456,
	.406
], t = [
	.229,
	.224,
	.225
], n = [
	"topLeft",
	"topRight",
	"bottomRight",
	"bottomLeft"
], r = null, i = /* @__PURE__ */ new Map(), a = null;
async function o() {
	return r ||= import("./scanic-ort.wasm.min-CD9Ls4bB.js").catch((e) => {
		throw r = null, /* @__PURE__ */ Error(`scanic: failed to load the ML runtime (onnxruntime-web). It is bundled with scanic's ESM build; if you use the UMD/CommonJS build, install it alongside scanic: \`npm install onnxruntime-web@1.23.x\`. (original error: ${e?.message || e})`);
	}), r;
}
async function s(e) {
	let t = e.assetBaseUrl ? (n = e.assetBaseUrl).endsWith("/") ? n : `${n}/` : "https://cdn.jsdelivr.net/npm/scanic-ml@0.2.0/dist/";
	var n;
	let r = e.modelUrl || `${t}doccornernet_lean.ort`, s = e.wasmPaths || t, c = (l = e.numThreads === void 0 ? e.threaded ? 4 : function() {
		if (typeof SharedArrayBuffer > "u" || (typeof window < "u" || typeof importScripts == "function") && !globalThis.crossOriginIsolated) return 1;
		let e = globalThis.navigator?.hardwareConcurrency || globalThis.process?.availableParallelism?.() || 4;
		return Math.max(2, Math.min(e, 4));
	}() : e.numThreads, a === null || l === a ? l : a);
	var l;
	let u = e.modelFetchTimeoutMs === void 0 ? 3e4 : e.modelFetchTimeoutMs, d = `${r}|${s}|${c}`;
	if (i.has(d)) return i.get(d);
	let f = (async () => {
		let t = await o();
		t.env.wasm.wasmPaths = s, t.env.wasm.numThreads = c, t.env.wasm.proxy = !1;
		let n = e.modelBytes || await async function(e, t) {
			let n = typeof AbortController < "u" && t > 0 ? new AbortController() : null, r = n ? setTimeout(() => n.abort(), t) : null;
			try {
				let t = await fetch(e, n ? { signal: n.signal } : void 0);
				if (!t.ok) throw Error(`scanic: failed to fetch the ML model from ${e} (HTTP ${t.status} ${t.statusText})`);
				return new Uint8Array(await t.arrayBuffer());
			} catch (r) {
				throw n?.signal.aborted ? Error(`scanic: timed out after ${t}ms fetching the ML model from ${e}`, { cause: r }) : r instanceof Error && r.message.startsWith("scanic:") ? r : Error(`scanic: failed to fetch the ML model from ${e} (${r?.message || r})`, { cause: r });
			} finally {
				r && clearTimeout(r);
			}
		}(r, u);
		return {
			ort: t,
			session: await t.InferenceSession.create(n, {
				executionProviders: ["wasm"],
				graphOptimizationLevel: "all"
			})
		};
	})(), p = a;
	a = c, i.set(d, f);
	try {
		return await f;
	} catch (e) {
		throw i.delete(d), i.size === 0 && (a = p), e;
	}
}
async function c(r, i = {}) {
	let a = [], { width: c, height: l } = function(e) {
		if (e && typeof e.width == "number" && typeof e.height == "number" && e.data) return {
			width: e.width,
			height: e.height
		};
		if (e) return {
			width: e.width || e.naturalWidth,
			height: e.height || e.naturalHeight
		};
		throw Error("No image provided");
	}(r), u = (typeof performance < "u" ? performance : Date).now(), { session: d } = await s(i);
	a.push({
		step: "ML Session Load",
		ms: ((typeof performance < "u" ? performance : Date).now() - u).toFixed(2)
	});
	let f = await o();
	u = (typeof performance < "u" ? performance : Date).now();
	let p = i.inputData || function(n) {
		let r = typeof OffscreenCanvas < "u", i = r ? new OffscreenCanvas(224, 224) : document.createElement("canvas");
		r || (i.width = 224, i.height = 224);
		let a = i.getContext("2d", { willReadFrequently: !0 });
		if (a.imageSmoothingEnabled = !0, a.imageSmoothingQuality = "medium", n && typeof n.width == "number" && typeof n.height == "number" && n.data) {
			let e = r ? new OffscreenCanvas(n.width, n.height) : document.createElement("canvas");
			r || (e.width = n.width, e.height = n.height), e.getContext("2d").putImageData(n, 0, 0), a.drawImage(e, 0, 0, n.width, n.height, 0, 0, 224, 224);
		} else {
			let e = n.width || n.naturalWidth, t = n.height || n.naturalHeight;
			a.drawImage(n, 0, 0, e, t, 0, 0, 224, 224);
		}
		let { data: o } = a.getImageData(0, 0, 224, 224), s = /* @__PURE__ */ new Float32Array(150528);
		for (let n = 0, r = 0; n < o.length; n += 4, r += 3) s[r] = (o[n] / 255 - e[0]) / t[0], s[r + 1] = (o[n + 1] / 255 - e[1]) / t[1], s[r + 2] = (o[n + 2] / 255 - e[2]) / t[2];
		return s;
	}(r), m = new f.Tensor("float32", p, [
		1,
		224,
		224,
		3
	]);
	a.push({
		step: "ML Preprocess",
		ms: ((typeof performance < "u" ? performance : Date).now() - u).toFixed(2)
	}), u = (typeof performance < "u" ? performance : Date).now();
	let h = await d.run({ [d.inputNames[0]]: m });
	a.push({
		step: "ML Inference",
		ms: ((typeof performance < "u" ? performance : Date).now() - u).toFixed(2)
	});
	let g = function(e, t, r) {
		let i = null, a = null;
		for (let t in e) {
			let n = e[t].data;
			n.length === 8 ? i = n : n.length === 1 && (a = n[0]);
		}
		if (!i) return null;
		let o = {};
		for (let e = 0; e < 4; e++) o[n[e]] = {
			x: i[2 * e] * t,
			y: i[2 * e + 1] * r
		};
		return {
			corners: o,
			score: a === null ? null : (s = a, 1 / (1 + Math.exp(-s)))
		};
		var s;
	}(h, c, l);
	if (!g) return {
		success: !1,
		corners: null,
		confidence: null,
		score: null,
		message: "ML model produced no coordinates",
		timings: a
	};
	let _ = i.minScore === void 0 ? .5 : i.minScore, v = g.score === null || g.score >= _;
	return {
		success: v,
		corners: g.corners,
		confidence: g.score,
		score: g.score,
		message: v ? "Document detected (ml)" : "No confident document (ml)",
		timings: a
	};
}
async function l(e = {}) {
	await s(e);
}
//#endregion
export { c as detectDocumentMl, l as initializeMl };
