const express = require('express');
const crypto = require('crypto');
const app = express();

app.use(express.json());
const EMAIL = "24f2002439@ds.study.iitm.ac.in";

app.post('/', (req, res) => {
    const body = req.body || {};
    const method = body.method;
    const msgId = body.id;

    if (method === "initialize") {
        return res.json({
            jsonrpc: "2.0",
            id: msgId,
            result: {
                protocolVersion: "2024-11-05",
                capabilities: {},
                serverInfo: { name: "exam-server", version: "1.0.0" }
            }
        });
    }
    
    if (method === "tools/list") {
        return res.json({
            jsonrpc: "2.0",
            id: msgId,
            result: {
                tools: [{
                    name: "solve_challenge",
                    description: "Solves the exam challenge using SHA-256",
                    inputSchema: { type: "object", properties: {} }
                }]
            }
        });
    }

    if (method === "tools/call") {
        const challenge = req.headers['x-exam-challenge'] || '';
        const textToHash = `${challenge}:${EMAIL}`;
        const hash = crypto.createHash('sha256').update(textToHash).digest('hex');
        const first16 = hash.substring(0, 16);

        return res.json({
            jsonrpc: "2.0",
            id: msgId,
            result: {
                content: [{ type: "text", text: first16 }]
            }
        });
    }

    res.json({ jsonrpc: "2.0" });
});

const listener = app.listen(process.env.PORT || 3000, () => {
    console.log("Your MCP Server is awake and listening!");
});
