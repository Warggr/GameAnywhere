<script setup>
import { ref } from "vue";
import RenameForm from "../components/name-form.vue";
import LoginForm from "../components/login-form.vue";
</script>

<template>
    <section class="hero">
        <div class="hero-copy">
            <h1>{{ game.game || "Lobby" }}</h1>
        </div>

        <aside class="sidebar">
            <section class="connection-card">
                <h2>Server Connection</h2>
                <div class="meta-list">
                    <div class="meta-row">
                        <span>Status</span>
                        <strong>{{ connection_status }}</strong>
                    </div>
                    <div class="meta-row">
                        <span>Server</span>
                        <strong>{{ server_host }}</strong>
                    </div>
                    <div class="meta-row">
                        <span>Room</span>
                        <strong>{{ room_id || "Unknown" }}</strong>
                    </div>
                </div>
            </section>

            <LoginForm />
        </aside>
    </section>

    <section class="page-grid">
        <div class="panel">
            <h2>Invite Link</h2>
            <div class="copyable-link">
                <input type="text" :value="invite_link()" readonly />
                <button type="button" @click="copyInviteLink($event)">
                    Copy
                </button>
            </div>
        </div>

        <div class="panel">
            <h2>Players</h2>
            <div class="seats-table">
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="(user, seat) in game.spectators"
                            :key="seat"
                            :class="{ 'own-player-row': isCurrentUser(seat) }"
                        >
                            <td>
                                <template v-if="isCurrentUser(seat)">
                                    <RenameForm
                                        :username="playername_editable_proxy"
                                    />
                                    <span class="status-pill">You</span>
                                </template>
                                <span v-else>{{ user.name || "Guest" }}</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <form
                v-if="ready_to_start"
                class="form-stack"
                @submit="finalizeRoom($event)"
            >
                <button type="submit">Start game</button>
            </form>
            <span v-else class="status-pill"
                >Still waiting for {{ waiting_count }} players...</span
            >
        </div>
    </section>
</template>

<script type="module">
import { applyPatch } from "fast-json-patch/index.mjs";
import { username as login_username } from "../src/login.ts";

export default {
    data() {
        const params = new URLSearchParams(window.location.search);
        return {
            socket: undefined,
            room_id: params.get("room"),
            seat_id: undefined,
            server_host: window.location.host,
            connection_status: "Connecting...",
            chosen_playername: login_username,
            playername_editable_proxy: this.get_playername_editable_proxy(),
            game: {
                spectators: [],
                num_players: undefined,
                game: undefined,
                you: undefined,
            },
        };
    },
    computed: {
        player_count() {
            return this.game.spectators.length;
        },
        expected_count() {
            return this.game.num_players?.const;
        },
        waiting_count() {
            if (this.expected_count === undefined) return 0;
            return Math.max(this.expected_count - this.player_count, 0);
        },
        ready_to_start() {
            return (
                this.expected_count !== undefined &&
                this.expected_count == this.player_count
            );
        },
        current_user() {
            const index = this.game.you?.spectator_index;
            if (index === undefined) return undefined;
            return this.game.spectators[index];
        },
    },

    async mounted() {
        const socket_url = new URL(
            "/lobby/" + this.room_id + "/ws/watch",
            window.location.href,
        );
        if (login_username) {
            socket_url.searchParams.append("username", login_username);
        }
        const socket = new WebSocket(socket_url);

        socket.onopen = (event) => {
            this.connection_status = "Connected";
        };
        socket.onerror = console.error;
        socket.onclose = (event) => {
            this.connection_status = "Disconnected";
        };
        socket.onmessage = async (message) => {
            this.handle_message(JSON.parse(message.data));
        };
        console.log("Set this.socket to", socket);
        this.socket = socket;
    },
    methods: {
        handle_message(message) {
            if (message.type == "finalize") {
                if (message.seat_id !== undefined) {
                    console.log("Set seat_id:", message.seat_id);
                    this.seat_id = message.seat_id;
                } else {
                    console.assert(this.seat_id !== undefined);
                    let url = new URL("player.html", window.location.href);
                    console.assert(message.location.startsWith("/r/"));
                    const room_id = message.location.substring(3);
                    url.searchParams.append("seat", this.seat_id);
                    url.searchParams.append("room", room_id);
                    window.location.replace(url);
                }
                return;
            }
            const oldIndex = this.game.you?.spectator_index;
            const removedBeforeMe = message.patch.filter(
                (patch) =>
                    patch.op === "remove" &&
                    patch.path.startsWith("/spectators/") &&
                    Number(patch.path.split("/")[2]) < oldIndex,
            ).length;
            this.game = applyPatch(this.game, message.patch).newDocument;
            if (removedBeforeMe > 0) {
                this.game.you.spectator_index = oldIndex - removedBeforeMe;
            }
        },
        invite_link() {
            let url = new URL(window.location.href);
            url.searchParams.delete("seat");
            return url;
        },
        async copyInviteLink(event) {
            const link = this.invite_link().toString();
            try {
                await navigator.clipboard.writeText(link);
            } catch (err) {
                const input = event.target.parentNode.firstElementChild;
                input.select();
                document.execCommand("copy");
            }
        },
        isCurrentUser(seat) {
            return seat === this.game.you?.spectator_index;
        },
        get_playername_editable_proxy() {
            let form_change = ref(
                this.game?.spectators[this.game?.you?.spectator_index]?.name ||
                    "",
            );
            let lobby_state = this;
            return {
                get() {
                    return form_change.value;
                },
                set(newName) {
                    form_change.value = newName;
                    lobby_state.socket.send(
                        JSON.stringify({
                            channel: "players",
                            op: "replace",
                            path: "/name",
                            value: newName,
                        }),
                    );
                    setTimeout(() => {
                        if (
                            lobby_state.game.spectators[
                                lobby_state.game.you.spectator_index
                            ].name != newName
                        ) {
                            form_change.value =
                                lobby_state.game.spectators[
                                    lobby_state.game.you.spectator_index
                                ];
                            alert("Couldn't reset username");
                        }
                    }, 5000);
                },
            };
        },
        finalizeRoom(event) {
            event.preventDefault();
            this.socket.send(
                JSON.stringify({
                    channel: "players",
                    op: "finalize",
                }),
            );
        },
    },
};
</script>
<style scoped></style>
