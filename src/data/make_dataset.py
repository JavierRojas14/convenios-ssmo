# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

import unicodedata

import pandas as pd


COLUMNA_A_UTILIZAR_PERSONAS = [
    "Nombre Funcionario",
    "Código Unidad",
    "Descripción Unidad",
    "Código Unidad 2",
    "Descripción Unidad 2",
]


def quitar_tildes(texto):
    # Normalizar el texto para descomponer los caracteres acentuados
    normalizado = unicodedata.normalize("NFD", texto)
    # Filtrar los caracteres diacríticos combinados
    texto_limpio = "".join(c for c in normalizado if not unicodedata.combining(c))
    return texto_limpio


def leer_y_limpiar_documentos(input_filepath):
    df = pd.read_excel(f"{input_filepath}/Reporte SSMOdigital Convenios.xlsx")
    print(f"> Shape i documentos: {df.shape[0]} documentos")
    # Limpia nombres de convenios
    df["NomRevisor"] = df["NomRevisor"].str.split().str.join(" ")
    df["NomRevisor"] = df["NomRevisor"].apply(quitar_tildes)

    # Limpia nombres de largo 4
    nombres_largo_4 = df["NomRevisor"].str.split().str.len() == 4
    nombres_convenios_largo_4_limpios = df[nombres_largo_4]["NomRevisor"].str.split()
    nombres_convenios_largo_4_limpios = (
        nombres_convenios_largo_4_limpios.str[0]
        + " "
        + nombres_convenios_largo_4_limpios.str[2]
        + " "
        + nombres_convenios_largo_4_limpios.str[3]
    )

    # Reemplaza los nombres de largo 4
    df.loc[nombres_largo_4, "NomRevisor"] = nombres_convenios_largo_4_limpios

    # Ordena documentos por fecha
    # df = df.query("Categoria == 'Convenio con Entidades Públicas'")
    df = df.sort_values(["NumInterno", "FechaHistorico"])

    # Calcula el timepo entre 2 acciones distintas para cada convenio
    df["tiempo_utilizado"] = df.groupby("NumInterno")["FechaHistorico"].diff()

    return df


def leer_y_limpiar_personas_ssmo(input_filepath):
    # Lee archivo de personas
    df_personas = df_personas = pd.read_excel(
        f"{input_filepath}/Plano DSSMO.xlsx",
        usecols=COLUMNA_A_UTILIZAR_PERSONAS,
    )

    # Elimina registros duplicados
    df_personas = df_personas.drop_duplicates()

    # Separa los nombres de los funcionario para llevarlos al formato
    nombres_separados = df_personas["Nombre Funcionario"].apply(quitar_tildes)
    nombres_separados = nombres_separados.str.split()
    df_personas["nombre_formateado"] = (
        nombres_separados.str[2] + " " + nombres_separados.str[0] + " " + nombres_separados.str[1]
    )

    return df_personas


def unir_documentos_y_personas(df_convenios, df_personas):
    convenios_con_procedencia = df_convenios.merge(
        df_personas, how="left", left_on="NomRevisor", right_on="nombre_formateado"
    )

    return convenios_con_procedencia


def asociar_convenios_con_resoluciones(df):
    tmp = df.copy()

    # Agrupa por cada uno de los convenios, y obtiene las resoluciones enlazadas al convenio
    convenios_con_resoluciones = tmp.groupby("DocConvAsociado")["NumInterno"].unique().astype(str)
    # Renombra la lista de resoluciones a un nombre apropiado
    convenios_con_resoluciones.name = "DocResAsociado"

    # Une los convenios con sus respectivas resoluciones
    df_con_convenios_asociados_a_resoluciones = (
        tmp.set_index("NumInterno")
        .merge(convenios_con_resoluciones, how="left", left_index=True, right_index=True)
        .reset_index(names="NumInterno")
    )

    return df_con_convenios_asociados_a_resoluciones


@click.command()
@click.argument("input_filepath", type=click.Path(exists=True))
@click.argument("output_filepath", type=click.Path())
def main(input_filepath, output_filepath):
    """Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).
    """
    logger = logging.getLogger(__name__)
    logger.info("making final data set from raw data")

    # Lee convenios y personas SSMO
    df_documentos = leer_y_limpiar_documentos(input_filepath)
    df_personas = leer_y_limpiar_personas_ssmo(input_filepath)

    # Une convenios y personas
    df_documentos_y_procedencia = unir_documentos_y_personas(df_documentos, df_personas)

    # Indica las resoluciones asociadas a convenios
    df_documentos_y_procedencia = asociar_convenios_con_resoluciones(df_documentos_y_procedencia)

    # Indica largo de datos limpios
    print(f"> Shape f documentos: {df_documentos_y_procedencia.shape[0]} documentos")

    # Guarda archivos
    df_documentos.to_csv(f"{output_filepath}/documentos_limpios.csv", index=False)
    df_personas.to_csv(f"{output_filepath}/personas_limpios.csv", index=False)
    df_documentos_y_procedencia.to_excel(
        f"{output_filepath}/documentos_y_procedencia.xlsx", index=False
    )


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
