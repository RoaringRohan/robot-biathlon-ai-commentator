import { NextResponse } from "next/server";
import snowflake from "snowflake-sdk";

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

export async function GET() {
    if (!process.env.SNOWFLAKE_ACCOUNT) {
        // Return empty if no creds yet, to avoid crashing frontend
        return NextResponse.json({ recordings: [] });
    }

    const connection = createConnection();

    try {
        await new Promise((resolve, reject) => {
            connection.connect((err, conn) => {
                if (err) reject(err);
                else resolve(conn);
            });
        });

        // Query top 5 recent logs
        const recordings = await new Promise((resolve, reject) => {
            connection.execute({
                sqlText: `
                    SELECT VIDEO_URL, TIMESTAMP, OFF_PATH_COUNT 
                    FROM MATCH_LOGS 
                    ORDER BY TIMESTAMP DESC 
                    LIMIT 5
                `,
                complete: (err, stmt, rows) => {
                    if (err) {
                        console.error("Query Failed: ", err.message);
                        reject(err);
                    } else {
                        // Transform rows to match frontend expectation
                        const formatted = (rows || []).map((row: any) => ({
                            filename: `Match ${row.OFF_PATH_COUNT} Errors`, // Creative naming or just timestamp
                            url: row.VIDEO_URL,
                            time: new Date(row.TIMESTAMP).toLocaleTimeString(),
                            timestamp: row.TIMESTAMP
                        }));
                        resolve(formatted);
                    }
                }
            });
        });

        return NextResponse.json({ recordings });

    } catch (error: any) {
        console.error("Fetch Error:", error);
        // Return empty on error to handle "table doesn't exist" gracefully
        return NextResponse.json({ recordings: [], error: error.message });
    }
}
