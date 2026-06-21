import { fileURLToPath, URL } from "node:url";

import { defineConfig, mergeConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import vueDevTools from "vite-plugin-vue-devtools";

// https://vite.dev/config/
/** @type {import('vite').UserConfig} */
const baseConfig = {
    base: "/web/",
    plugins: [vue(), vueJsx(), vueDevTools()],
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    build: {
        rolldownOptions: {
            input: {
                index: "index.html",
                lobby: "lobby.html",
                player: "player.html",
            },
        },
    },
};

export default defineConfig(({ mode }) => {
    if (mode == "development") {
        return mergeConfig(baseConfig, {
            build: {
                cssMinify: false,
                minify: false,
            },
        });
    } else {
        return baseConfig;
    }
});
