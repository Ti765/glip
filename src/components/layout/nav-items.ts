
import type { LucideIcon } from "lucide-react";
import { LayoutDashboard, Tags, Split, FileArchive, BrainCircuit } from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  label?: string;
  disabled?: boolean;
}

export const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    label: "Visão Geral",
  },
  {
    title: "Classificar Fornecedores",
    href: "/classify-suppliers",
    icon: Tags,
    label: "Classificação",
  },
  {
    title: "Separar CT-e por Regime",
    href: "/separate-cte",
    icon: Split,
    label: "CT-e",
  },
  {
    title: "Separar XML por Tipo",
    href: "/separate-xml",
    icon: FileArchive,
    label: "NF-e",
  },
  {
    title: "Análise de Divergências",
    href: "/analyze-discrepancies",
    icon: BrainCircuit,
    label: "IA Insights",
  },
];
