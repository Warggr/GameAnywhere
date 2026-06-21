<script setup>
const props = defineProps(["username"]);
let username = props.username;
let name_editing = false;
let name_draft = username.get();

function finishNameEdit() {
    name_editing = false;
    submitNameChange();
}

function resetNameDraft() {
    name_draft = username.get();
}

function submitNameChange() {
    name_editing = false;
    const newName = name_draft.trim();
    if (newName === "" || newName === username.get()) {
        resetNameDraft();
        return;
    }
    username.set(newName);
}
</script>

<template>
    <form class="player-name-form" @submit.prevent="submitNameChange">
        <input
            type="text"
            v-model="name_draft"
            @focus="name_editing = true"
            @blur="finishNameEdit"
            @keydown.esc.prevent="resetNameDraft"
            aria-label="Your username"
        />
    </form>
</template>
