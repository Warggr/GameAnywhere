export const username = document.cookie
    .split("; ")
    .find((row) => row.startsWith("username="))
    ?.split("=")[1];
