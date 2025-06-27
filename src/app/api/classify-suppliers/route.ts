import { NextRequest, NextResponse } from "next/server";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { tmpdir } from "node:os";
import { randomUUID } from "crypto";
import { execFileSync } from "node:child_process";

export const dynamic = "force-dynamic"; // garante runtime Node

export async function POST(req: NextRequest) {
  try {
    /* ---------- 1. Lê o multipart ---------- */
    const form     = await req.formData();
    const empresa  = form.get("empresa") as string;
    const dataIni  = form.get("dataIni") as string;
    const dataFim  = form.get("dataFim") as string;
    const files    = form.getAll("files") as File[];

    if (!empresa || !dataIni || !dataFim || files.length === 0) {
      return NextResponse.json({ ok: false, error: "Campos faltando." }, { status: 400 });
    }

    /* ---------- 2. Cria diretório tmp e grava arquivos ---------- */
    const workDir = join(tmpdir(), `job_${randomUUID()}`);
    mkdirSync(workDir, { recursive: true });

    for (const f of files) {
      const dest = join(workDir, f.name);          // mantém subpastas (ex.: ENT#RADAS/…)
      mkdirSync(dirname(dest), { recursive: true });
      const buf  = Buffer.from(await f.arrayBuffer());
      writeFileSync(dest, buf);
    }

    /* ---------- 3. Executa o script Python ---------- */
    const scriptPath = join(
      process.cwd(),
      "src",
      "app",
      "classify-suppliers",
      "Classificador_v1.py"
    );

    const args = [
      scriptPath,
      "--input-dir", workDir,
      "--empresa",   empresa,
      "--data-ini",  dataIni,
      "--data-fim",  dataFim,
    ];

    // Usa variável PYTHON_BIN se definida; senão, tenta "python3"
    const PY = process.env.PYTHON_BIN || "/home/user/.nix-profile/bin/python3";
    const output = execFileSync(PY, args, { encoding: "utf-8" });

    /* ---------- 4. Limpa e responde ---------- */
    rmSync(workDir, { recursive: true, force: true });
    return NextResponse.json({ ok: true, log: output });
  } catch (err: any) {
    console.error(err);
    return NextResponse.json({ ok: false, error: err.message }, { status: 500 });
  }
}
