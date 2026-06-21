<script setup>
import { username } from "../src/login";

let username_attempt = "";
</script>

<template>
    <section class="login-card">
        <h2>Login</h2>
        <form
            v-if="username === undefined"
            class="form-stack"
            @submit.prevent="login"
        >
            <div class="field">
                <label for="login-username">Username</label>
                <input
                    id="login-username"
                    type="text"
                    v-model="username_attempt"
                />
            </div>
            <button type="submit">Login</button>
        </form>
        <form v-else class="form-stack" @submit.prevent="logout">
            <div class="status-line">
                <span>Logged in as</span>
                <strong>{{ username }}</strong>
            </div>
            <button class="secondary" type="submit">Log out</button>
        </form>
    </section>
</template>

<script type="module">
export default {
    methods: {
        login() {
            fetch("/login", {
                method: "POST",
                body: JSON.stringify({
                    username: this.username_attempt,
                }),
            })
                .then((res) => {
                    console.assert(res.success);
                    this.username = this.username_attempt;
                })
                .catch((e) => {
                    alert("Couldn't log in!");
                });
        },
        logout() {
            document.cookie =
                "username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/";
            this.username = undefined;
        },
    },
};
</script>
