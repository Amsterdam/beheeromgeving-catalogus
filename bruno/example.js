// Example code to use in the script section to authorize.
const getToken = require("./get-token");

const token = await getToken(["scope_dadi"]);

req.setHeader("Authorization", `Bearer ${token}`);
