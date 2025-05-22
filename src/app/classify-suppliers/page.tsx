
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UploadCloud, Tags } from "lucide-react";

export default function ClassifySuppliersPage() {
  return (
    <div className="space-y-8">
      <header className="flex items-center space-x-3">
        <Tags className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Classificar Fornecedores</h1>
          <p className="text-muted-foreground">
            Importe arquivos XML e classifique-os por fornecedor utilizando o histórico de acumuladores.
          </p>
        </div>
      </header>

      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Importar Arquivos XML</CardTitle>
          <CardDescription>
            Selecione ou arraste os arquivos XML para iniciar a classificação por fornecedor.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid w-full max-w-lg items-center gap-2">
            <Label htmlFor="xml-files-suppliers" className="sr-only">Arquivos XML</Label>
            <Input id="xml-files-suppliers" type="file" multiple className="cursor-pointer file:text-primary file:font-semibold hover:file:bg-primary/10" />
          </div>
          
          <div className="border-2 border-dashed border-border rounded-lg p-12 flex flex-col items-center justify-center text-center bg-muted/20 hover:border-primary transition-colors">
            <UploadCloud className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground mb-1">Arraste e solte os arquivos XML aqui</p>
            <p className="text-sm text-muted-foreground">ou clique para selecionar</p>
          </div>

          <Button size="lg" className="w-full sm:w-auto bg-gradient-to-r from-primary via-blue-600 to-purple-600 hover:opacity-90 text-primary-foreground">
            <UploadCloud className="mr-2 h-5 w-5" />
            Iniciar Classificação
          </Button>
        </CardContent>
      </Card>

      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Resultados da Classificação</CardTitle>
          <CardDescription>
            Após o processamento, os fornecedores classificados serão exibidos aqui.
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
