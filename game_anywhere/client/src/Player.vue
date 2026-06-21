<script setup>
import Page from "../views/page.vue";
import LoginForm from "../components/login-form.vue";
import RenameForm from "../components/name-form.vue";
import { Screen } from "./screen.js";
</script>

<template>
    <Page>
        <div class="play-grid">
            <aside class="sidebar">
                <section class="connection-card">
                    <h2>Server Connection</h2>
                    <div class="meta-list">
                        <div class="meta-row">
                            <span>Status</span>
                            <strong>{{ connection_status }}</strong>
                        </div>
                        <div class="meta-row">
                            <span>Player</span>
                            <strong>{{ player_name }}</strong>
                        </div>
                    </div>
                    <form class="join-form" @submit="connectToServer">
                        <div class="field">
                            <label for="serverUrl">Server address</label>
                            <input
                                type="text"
                                v-model="serverUrl"
                                placeholder="localhost:8080"
                            />
                        </div>
                        <div class="field">
                            <label for="playerId">Seat number</label>
                            <input
                                type="text"
                                v-model="playerId"
                                placeholder="0"
                            />
                        </div>
                        <div class="field">
                            <label for="roomId">Room ID</label>
                            <input
                                type="text"
                                v-model="roomId"
                                placeholder="Enter room ID"
                            />
                        </div>
                        <button
                            :disabled="connection_status == 'Connected'"
                            type="submit"
                        >
                            Join room
                        </button>
                    </form>
                    <ul>
                        <li v-for="player in connected_players">
                            {{ player.name }}
                        </li>
                    </ul>
                </section>
                <RenameForm :username="playername_editable_proxy" />
                <LoginForm />
            </aside>

            <!-- Screen Panel -->
            <div id="screen-shadow-host" />

            <!-- Chat Log and Input -->
            <div id="logPanel">
                <form
                    id="chatInput"
                    :hidden="~can_chat"
                    onsubmit="
                        sendChatLine(this);
                        return false;
                    "
                >
                    <input type="text" placeholder="Type a message..." />
                    <button type="submit">Send</button>
                </form>
            </div>

            <dialog id="winnerDialog">
                <h1>Konec hry</h1>
                <p>Winner: <span id="winner"></span></p>
            </dialog>
        </div>

        <div id="controlPanel" hidden>
            <span v-for="line in logLines" class="log-message">
                <b>{{ line.author }}</b
                >{{ line.text }}
            </span>
        </div>
    </Page>
</template>

<script type="module">
import { username } from "../src/login.ts";
import { applyPatch } from "fast-json-patch";
import { makeWord, readWord } from "wizard/wizard.js";

const urlParams = new URLSearchParams(window.location.search);
let player_name = urlParams.get("username") || username;
if (player_name === undefined) {
    console.log(player_name, "reloading the page...");
    player_name = "guest" + Math.round(Math.random() * 100);
    let new_url = new URL(window.location.href);
    new_url.searchParams.append("username", player_name);
    window.history.pushState(null, null, new_url); // Make a page reload keep the guestId
}
console.log(player_name);

let screen_resolve, screen_reject;

export default {
    data() {
        return {
            connection_status: "Not connected",
            socket: undefined,
            roomId: urlParams.get("room"),
            playerId: urlParams.get("seat"),
            player_name: player_name,
            serverAddress: urlParams.get("serverUrl") || window.location.host,
            logLines: [],
            can_chat: false,
            connected_players: [],
            screen: new Promise((resolve, reject) => {
                screen_resolve = resolve;
                screen_reject = reject;
            }),
        };
    },
    mounted() {
        fetch(`http://${this.serverAddress}/r/${this.roomId}/connected/`).then(
            (res) => {
                this.connected_players = res.json();
            },
        );

        if (this.roomId !== undefined) {
            this.connectToServer();
        }
    },
    methods: {
        async connectToServer() {
            fetch(
                "http://" +
                    this.serverAddress +
                    "/r/" +
                    this.roomId +
                    "/html?seat=" +
                    this.playerId +
                    (this.player_name
                        ? ""
                        : "&username=" + encodeURIComponent(this.player_name)),
            )
                .then((response) => response.text())
                .then((html) => {
                    const screen = new Screen(
                        document.getElementById("screen-shadow-host"),
                        html,
                    );
                    console.log("Resolving Screen with", screen);
                    screen_resolve(screen);
                });

            this.connection_status = "Connecting...";
            if (window.WebSocket === undefined) {
                this.connection_status = "WebSockets not supported!";
                throw new Error("WebSockets not supported!");
            }

            this.socket = new WebSocket(
                "ws://" +
                    this.serverAddress +
                    "/r/" +
                    this.roomId +
                    "/ws/" +
                    this.playerId +
                    (this.player_name
                        ? ""
                        : "?username=" + encodeURIComponent(this.player_name)),
            );
            this.socket.onopen = (event) => {
                this.connection_status = "Connected";
                this.socket.send(
                    JSON.stringify({ channel: "game", data: "?" }),
                ); // In case we just reconnected and the server is waiting for us to answer a question
            };
            this.socket.onclose = (event) => {
                this.connection_status = "Not connected";
            };
            this.socket.onerror = console.error;

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === "choice") {
                    this.screen.then((screen) => {
                        if (data.message) {
                            controlPanel.hidden = false;
                            const banner = document.createElement("span");
                            banner.innerText = data.message;
                            controlPanel.appendChild(banner);
                        }
                        if (data.slots) {
                            let slots = data.slots.map((id) => {
                                let e = screen.lookupSlot(id);
                                e.setAttribute("data-chosen", id);
                                return e;
                            });
                            let eventListener = (event) => {
                                endChoices(
                                    event.currentTarget.getAttribute(
                                        "data-chosen",
                                    ),
                                );
                            };
                            let endChoices = (chosenComponent) => {
                                slots.forEach((c) => {
                                    c.removeEventListener(
                                        "click",
                                        eventListener,
                                    );
                                    c.classList.remove("clickable");
                                    c.removeAttribute("data-chosen");
                                });
                                controlPanel.innerHTML = "";
                                controlPanel.hidden = true;
                                this.socket.send(
                                    JSON.stringify({
                                        channel: "game",
                                        data: chosenComponent,
                                    }),
                                );
                            };
                            slots.forEach((c) => {
                                c.addEventListener("click", eventListener);
                                c.classList.add("clickable");
                            });
                            if (data.special_options) {
                                controlPanel.hidden = false;
                                for (let option of data.special_options) {
                                    const button =
                                        document.createElement("button");
                                    button.textContent = option;
                                    button.addEventListener("click", (_event) =>
                                        endChoices(option),
                                    );
                                    controlPanel.appendChild(button);
                                }
                            }
                        } else if (
                            data.schema &&
                            data.schema.type == "string" &&
                            data.schema.enum
                        ) {
                            let form = document.createElement("form");
                            let btn_handler = (event) => {
                                event.preventDefault();
                                let answer = event.target.textContent;
                                this.socket.send(
                                    JSON.stringify({
                                        channel: "game",
                                        data: answer,
                                    }),
                                );
                                controlPanel.removeChild(form);
                                controlPanel.hidden = true;
                            };
                            for (let option of data.schema.enum) {
                                let btn = document.createElement("button");
                                btn.textContent = option;
                                btn.type = "submit";
                                btn.onclick = btn_handler;
                                form.appendChild(btn);
                            }
                            controlPanel.appendChild(form);
                            controlPanel.hidden = false;
                        } else if (data.schema) {
                            let formContent = makeWord(data.schema);
                            let form = document.createElement("form");
                            form.appendChild(formContent);
                            let submitButton = document.createElement("button");
                            submitButton.type = "submit";
                            submitButton.textContent = "Submit";
                            submitButton.classList.add("clickable");
                            form.appendChild(submitButton);
                            form.onsubmit = (event) => {
                                event.preventDefault();
                                let answer = readWord(formContent);
                                this.socket.send(
                                    JSON.stringify({
                                        channel: "game",
                                        data: answer,
                                    }),
                                );
                                controlPanel.removeChild(form);
                                controlPanel.hidden = true;
                            };
                            controlPanel.appendChild(form);
                            controlPanel.hidden = false;
                        } else
                            console.warn(
                                "Unrecognized server message: unrecognized choice type:",
                                data,
                            );
                    });
                } else if (data.type === "chatcontrol") {
                    if (data.set === "on") {
                        this.can_chat = true;
                    } else {
                        this.can_chat = false;
                    }
                } else if (data.type === "message") {
                    this.logLines.push({
                        author: data.sender,
                        text: data.text,
                    });
                } else if (data.type === "game_update") {
                    this.screen.then((screen) => {
                        console.warn(screen);
                        if (data.summary !== undefined) {
                            const dialog =
                                document.getElementById("winnerDialog");
                            dialog.querySelector("#winner").textContent =
                                data.summary.players[data.summary.winner];
                            dialog.show();
                            return;
                        }
                        console.assert(Array.isArray(data.patch));
                        for (let diff of data.patch) {
                            if (diff.op == "replace") {
                                screen.replace(diff.path, diff.value);
                            } else if (diff.op == "add") {
                                screen.add(diff.path, diff.value);
                            } else if (diff.op == "remove") {
                                screen.remove(diff.path);
                            } else {
                                console.warn("Unrecognized diff: " + diff);
                            }
                        }
                    });
                } else if (data.type == "room_update") {
                    applyPatch(this.connected_players, data.patch);
                } else
                    console.warn(
                        "Unrecognized server message: unknown type:",
                        data,
                    );
            };
        },

        sendChatLine(form) {
            let line = form.firstElementChild.value;
            this.socket.send(JSON.stringify({ channel: "chat", data: line }));
            this.lines.push({ author: "You", content: line });
        },
    },
};
</script>
