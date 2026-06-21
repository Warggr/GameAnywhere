import gameCssUrl from "../css/screen.css?url";
import playerCssUrl from "../css/player.css?url";

export class Screen {
    constructor(rootNode, html) {
        const shadow = rootNode.attachShadow({ mode: "open" });
        const screen = document.createElement("div");
        shadow.appendChild(screen);
        screen.setAttribute("data-key", "");
        screen.classList.add("ga-composite");
        screen.innerHTML = html;

        this.loaded_css = new Set();
        this.loaded_js = new Set();
        for (const elem of screen.querySelectorAll("script")) {
            this.ensureJS(elem.src);
        }

        const sheets = [playerCssUrl, gameCssUrl].map((link) =>
            fetch(link)
                .then((res) => res.text())
                .then((css) => new CSSStyleSheet().replace(css)),
        );
        Promise.all(sheets).then(
            (sheets) => (shadow.adoptedStyleSheets = sheets),
        );
        this.screen = screen;
    }
    getLogicalParent(element) {
        let p = element.parentElement;
        while (p !== null && !p.hasAttribute("data-key")) {
            p = p.parentElement;
        }
        return p;
    }
    /*
    model:
    slot.ga-slot[data-key="..."] { (e.g. <li>)
    wrappers ... { (these can collapse; actually the slot and the component could be the same)
    component.ga-composite {
    slot.ga-slot[data-key="..."] {

    */
    getLogicalChild(parent, segment) {
        console.assert(
            parent.hasAttribute("data-key") || parent.id == "screen",
            parent,
        );
        return Array.from(
            parent.querySelectorAll(`[data-key="${segment}"]`),
        ).find((el) => this.getLogicalParent(el) === parent);
    }
    lookupSlot(address) {
        let slot = this.screen;
        console.assert(address.startsWith("/"));
        address = address.slice(1);
        for (let segment of address.split("/")) {
            slot = this.getLogicalChild(slot, segment);
            console.assert(slot !== undefined, segment);
            console.assert(slot.classList.contains("ga-slot"), slot);
        }
        return slot;
    }
    async ensureJS(scriptname) {
        if (this.loaded_js.has(scriptname)) return;
        this.loaded_js.add(scriptname);
        await import(scriptname);
    }
    async ensureCSS(sheetname) {
        if (this.loaded_css.has(sheetname)) return;
        this.loaded_css.add(sheetname);
        let link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", sheetname);
        document.head.appendChild(link);
    }
    remove(path) {
        let key = path.split("/");
        let child_num = key.pop();
        let parent_slot = this.lookupSlot(key.join("/"));
        let child = this.getLogicalChild(parent_slot, child_num);
        child.innerText = "";
    }
    add(path, content) {
        let DOMConstructionSite = document.createElement("div");
        DOMConstructionSite.innerHTML = content; // TODO: find a more elegant way of parsing HTML
        path = path.split("/").slice(0, -1).join("/");
        let parent = this.lookupSlot(path);
        let appendSite;
        console.assert(
            parent.hasAttribute("data-key") &&
                parent.classList.contains("ga-slot"),
        );
        if (parent.classList.contains("ga-composite")) {
            appendSite = parent;
        } else {
            appendSite = [...parent.querySelectorAll(".ga-composite")].find(
                (el) => this.getLogicalParent(el) == parent,
            );
        }
        console.assert(appendSite !== undefined, parent);
        console.assert(
            DOMConstructionSite.firstChild.classList.contains("ga-slot"),
        );
        appendSite.append(DOMConstructionSite.firstChild);
    }
    replace(path, content) {
        let DOMConstructionSite = document.createElement("div");
        DOMConstructionSite.innerHTML = content;
        let realElems = [];
        for (const elem of DOMConstructionSite.children) {
            if (elem.nodeName == "script") {
                this.ensureJS(elem.src);
            } else if (elem.nodeName == "link") {
                console.assert(elem.rel == "stylesheet");
                this.ensureCSS(elem.href);
            } else {
                realElems.push(elem);
            }
        }
        console.assert(realElems.length == 1, realElems);
        this.lookupSlot(path).replaceWith(realElems[0]);
    }
}
