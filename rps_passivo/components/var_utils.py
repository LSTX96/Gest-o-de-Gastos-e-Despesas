"""Pequeno helper: garante que um valor indexado de um dict/Var vire uma
StringVar de verdade, para poder ser concatenado com '+' nos componentes."""
import reflex as rx


def vstr(valor) -> rx.Var:
    return rx.Var.create(valor).to(str)
