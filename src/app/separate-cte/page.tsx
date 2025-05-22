
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UploadCloud, Split } from "lucide-react";

export default function SeparateCtePage() {
  return (
    <div className="space-y-8">
      <header className="flex items-center space-x-3">
        <Split className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Separar CT-e por Regime Tributário</h1>
          <p className="text-muted-foreground">
            Importe arquivos CT-e para separá-los com base no regime tributário (CRT) contido em cada um.
          </p>
        </div>
      </header>

      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Importar Arquivos CT-e</CardTitle>
          <CardDescription>
            Selecione ou arraste os arquivos CT-e (Conhecimento de Transporte Eletrônico).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid w-full max-w-lg items-center gap-2">
            <Label htmlFor="cte-files" className="sr-only">Arquivos CT-e</Label>
            <Input id="cte-files" type="file" multiple className="cursor-pointer file:text-primary file:font-semibold hover:file:bg-primary/10" />
          </div>
          
          <div className="border-2 border-dashed border-border rounded-lg p-12 flex flex-col items-center justify-center text-center bg-muted/20 hover:border-primary transition-colors">
            <UploadCloud className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground mb-1">Arraste e solte os arquivos CT-e aqui</p>
            <p className="text-sm text-muted-foreground">ou clique para selecionar</p>
          </div>

          <Button size="lg" className="w-full sm:w-auto bg-gradient-to-r from-primary via-blue-600 to-purple-600 hover:opacity-90 text-primary-foreground">
            <UploadCloud className="mr-2 h-5 w-5" />
            Iniciar Separação de CT-e
          </Button>
        </CardContent>
      </Card>

      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Resultados da Separação</CardTitle>
          <CardDescription>
            Os arquivos CT-e separados por regime tributário serão listados aqui após o processamento.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-40 bg-muted/50 rounded-md">
            <p className="text-muted-foreground">Nenhum arquivo processado ainda.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
