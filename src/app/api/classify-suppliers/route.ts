// src/app/api/classify-suppliers/route.ts
import { NextRequest, NextResponse } from "next/server";
import { writeFileSync, rmSync } from "fs";
import { mkdir } from "fs/promises";
import { join, basename, resolve } from "path";
import { randomUUID } from "crypto";
import { spawn } from "child_process";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  // 1) Cria pasta tmp/job_<UUID>/input
  const jobId = randomUUID();
  const baseTmp = join(process.cwd(), "tmp", `job_${jobId}`);
  const inputDir = join(baseTmp, "input");
  await mkdir(inputDir, { recursive: true });

  try {
    // 2) Grava cada upload usando só o basename
    const form = await req.formData();
    const files = form.getAll("files") as File[];
    for (const f of files) {
      const buf = Buffer.from(await f.arrayBuffer());
      const fn = basename(f.name);
      writeFileSync(join(inputDir, fn), buf);
    }

    // 3) Pega demais campos do formulário
    const empresa = form.get("empresa")?.toString() ?? "";
    const dataIni = form.get("dataIni")?.toString() ?? "";
    const dataFim = form.get("dataFim")?.toString() ?? "";

    // 4) Local absoluto do script Python
    const script = join(
      process.cwd(),
      "src",
      "app",
      "classify-suppliers",
      "Classificador_v1.py"
    );

    // 5) Monta argumentos
    const args = [
      script,
      "--input-dir",
      inputDir,
      "--empresa",
      empresa,
      "--data-ini",
      dataIni,
      "--data-fim",
      dataFim,
    ];

    // 6) Escolhe o python: primeiro o .venv/bin/python3, senão o python3 do sistema
    const venvPy = resolve(process.cwd(), ".venv", "bin", "python3");
    const PY =
      process.env.PYTHON_BIN ||
      (require("fs").existsSync(venvPy) ? venvPy : "python3");

    // 6.1) Log para confirmar que o Node vê as variáveis ODBC
    console.log("🔧 ODBCSYSINI: ", process.env.ODBCSYSINI);
    console.log("🔧 ODBCINI:    ", process.env.ODBCINI);
    console.log("🔧 ODBCINSTINI:", process.env.ODBCINSTINI);

    // 7) Chama o Python de forma assíncrona, garantindo que herde o env
    const pythonProcess = spawn(PY, args, {
      env: {
        ...process.env,
        ODBCSYSINI:  process.env.ODBCSYSINI!,
        ODBCINI:     process.env.ODBCINI!,
        ODBCINSTINI: process.env.ODBCINSTINI!,
      },
    });

    let stdout = "";
    let stderr = "";

    pythonProcess.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    return new Promise<NextResponse>((resolve) => {
      pythonProcess.on("close", (code) => {
        // 8) Limpa todo o tmp
        rmSync(baseTmp, { recursive: true, force: true });

        if (code === 0) {
          resolve(NextResponse.json({ ok: true, log: stdout }));
        } else {
          console.error("classify-suppliers error:", stderr);
          resolve(
            NextResponse.json(
              { ok: false, error: stderr || "Erro desconhecido no script Python" },
              { status: 500 }
            )
          );
        }
      });
    });
  } catch (err: any) {
    console.error("classify-suppliers error:", err);
    // 8) Limpa todo o tmp
    rmSync(baseTmp, { recursive: true, force: true });
    return NextResponse.json(
      { ok: false, error: err.message || String(err) },
      { status: 500 }
    );
  }
}
