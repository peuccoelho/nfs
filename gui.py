import asyncio
import tkinter as tk
from tkinter import messagebox, ttk

from portal import PortalNFSE
from config import Config
from utils import setup_logging, get_logger

logger = get_logger(__name__)


def rodar():
    """Callback do botao: le mes/ano e inicia a exportacao."""
    try:
        mes = int(combo_mes.get())
        ano = int(combo_ano.get())
    except ValueError:
        messagebox.showerror("Erro", "Selecione mes e ano validos")
        return

    config = Config()
    config.mes = mes
    config.ano = ano

    if not config.usuario or not config.senha:
        messagebox.showerror(
            "Erro", "Preencha o arquivo .env com USUARIO e SENHA"
        )
        return

    btn.config(state="disabled", text="Executando...")
    status.config(text="Processando...")

    async def executar():
        portal = PortalNFSE(config)
        try:
            await portal.iniciar()
            await portal.navegar_para_nota_fiscal()
            await portal.executar_consulta()
            logger.info("Exportacao concluida com sucesso!")
            status.config(text="Concluido!")
            messagebox.showinfo("Sucesso", "Exportacao finalizada!")
        except Exception as e:
            logger.error("Erro: %s", e)
            status.config(text="Erro! Veja o log")
            messagebox.showerror("Erro", str(e))
        finally:
            await portal.fechar()
            btn.config(state="normal", text="Iniciar")

    asyncio.run(executar())


# --- Interface ---
root = tk.Tk()
root.title("Exportador NFS-e - Camacari")
root.geometry("320x220")
root.resizable(False, False)

tk.Label(root, text="Exportador de XMLs NFS-e", font=("Arial", 12, "bold")).pack(pady=10)

frame = ttk.Frame(root, padding=10)
frame.pack()

ttk.Label(frame, text="Mes:").grid(row=0, column=0, sticky="w", pady=5)
combo_mes = ttk.Combobox(
    frame, values=[f"{m:02d}" for m in range(1, 13)], width=8, state="readonly"
)
combo_mes.grid(row=0, column=1, pady=5)
combo_mes.set("05")

ttk.Label(frame, text="Ano:").grid(row=1, column=0, sticky="w", pady=5)
combo_ano = ttk.Combobox(
    frame, values=[str(a) for a in range(2024, 2031)], width=8, state="readonly"
)
combo_ano.grid(row=1, column=1, pady=5)
combo_ano.set("2026")

btn = ttk.Button(root, text="Iniciar", command=rodar)
btn.pack(pady=10)

status = ttk.Label(root, text="Pronto", foreground="gray")
status.pack()

root.mainloop()
