import { NextResponse } from "next/server";
import snowflake from "snowflake-sdk";
import fs from "fs";
import path from "path";
import { v4 as uuidv4 } from "uuid";
import os from "os";

// Helper to create Snowflake connection
function createConnection() {
    return snowflake.createConnection({
        account: process.env.SNOWFLAKE_ACCOUNT || "",
        username: process.env.SNOWFLAKE_USER || "",
        password: process.env.SNOWFLAKE_PASSWORD || "",
        database: process.env.SNOWFLAKE_DATABASE || "",
        schema: process.env.SNOWFLAKE_SCHEMA || "",
        warehouse: process.env.SNOWFLAKE_WAREHOUSE || "COMPUTE_WH"
    });
}

export async function POST(req: Request) {
    let connection;

    try {
        const formData = await req.formData();
        const file = formData.get("file") as File;

        if (!file) {
            return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
        }

        if (!process.env.SNOWFLAKE_ACCOUNT) {
            console.error("Missing Snowflake credentials");
            return NextResponse.json({ error: "Server configuration error: Missing Snowflake credentials" }, { status: 500 });
        }

        // 1. Save file locally temporarily
        const buffer = Buffer.from(await file.arrayBuffer());
        const tempDir = os.tmpdir();
        const fileName = `match_${Date.now()}_${uuidv4()}.webm`;
        const filePath = path.join(tempDir, fileName);

        fs.writeFileSync(filePath, buffer);

        // 2. Connect to Snowflake
        connection = createConnection();
        await new Promise((resolve, reject) => {
            connection.connect((err, conn) => {
                if (err) {
                    console.error("Unable to connect: " + err.message);
                    reject(err);
                } else {
                    resolve(conn);
                }
            });
        });

        // 3. Upload to Stage
        // Using @VIDEO_STAGE internal stage
        // AUTO_COMPRESS = FALSE (as requested)
        // ENCRYPTION = SNOWFLAKE_SSE (as requested)
        console.log(`Uploading ${fileName} to Snowflake stage...`);

        await new Promise((resolve, reject) => {
            connection.execute({
                sqlText: `PUT file://${filePath.replace(/\\/g, '/')} @VIDEO_STAGE AUTO_COMPRESS=FALSE`,
                complete: (err, stmt, rows) => {
                    if (err) {
                        console.error("PUT Failed: ", err.message);
                        reject(err);
                    } else {
                        console.log("Upload complete: ", rows);
                        resolve(rows);
                    }
                }
            });
        });

        // 4. Clean up local file
        fs.unlinkSync(filePath);

        // 5. Generate Scoped URL (Presigned URL equivalent)
        // This allows the frontend to replay it immediately
        // Note: GET_PRESIGNED_URL might vary based on cloud provider (AWS/Azure/GCP) backing Snowflake. 
        // For internal stages, we often use `get_presigned_url`.

        // However, standard SQL approach involves calling a system function or just returning success 
        // if we can't easily generate a public link without integration.
        // Let's try to generate a presigned URL using SQL if possible, or just return success.

        // NOTE: Generating a scoped URL via SQL:
        // SELECT GET_PRESIGNED_URL(@VIDEO_STAGE, 'filename.webm', 3600);

        let playbackUrl = "";
        try {
            const urlResult: any[] = await new Promise((resolve, reject) => {
                connection.execute({
                    sqlText: `SELECT GET_PRESIGNED_URL(@VIDEO_STAGE, '${fileName}', 3600) as url`,
                    complete: (err, stmt, rows) => {
                        if (err) reject(err);
                        else resolve(rows || []);
                    }
                });
            });

            if (urlResult && urlResult.length > 0) {
                playbackUrl = urlResult[0].URL || urlResult[0].url; // Case sensitivity check
            }
        } catch (e) {
            console.warn("Could not generate presigned URL, ignoring:", e);
        }

        // 6. Insert into MATCH_LOGS
        // Schema: MATCH_ID STRING, TIMESTAMP..., VIDEO_URL STRING, OFF_PATH_COUNT INT
        const matchId = uuidv4();
        const offPathCount = formData.get("offPathCount") || "0";

        console.log(`Inserting into MATCH_LOGS: ${matchId}, Count: ${offPathCount}`);

        await new Promise((resolve, reject) => {
            connection.execute({
                sqlText: `INSERT INTO MATCH_LOGS (MATCH_ID, VIDEO_URL, OFF_PATH_COUNT) VALUES (?, ?, ?)`,
                binds: [matchId, playbackUrl || fileName, parseInt(offPathCount.toString())],
                complete: (err, stmt, rows) => {
                    if (err) {
                        console.error("INSERT Failed: ", err.message);
                        // We don't fail the whole request since upload succeeded
                        resolve(null);
                    } else {
                        console.log("Log Inserted: ", rows);
                        resolve(rows);
                    }
                }
            });
        });

        return NextResponse.json({
            success: true,
            matchId: matchId,
            filename: fileName,
            playbackUrl: playbackUrl
        });

    } catch (error: any) {
        console.error("Upload Error:", error);
        return NextResponse.json(
            { error: error.message || "Upload failed" },
            { status: 500 }
        );
    }
}
