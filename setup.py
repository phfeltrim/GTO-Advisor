# Salve este arquivo como: setup.py (Substituindo a versão anterior)

from setuptools import setup, Extension # <-- ESTA É A LINHA CORRIGIDA
import os

# O nome do módulo que vamos importar no Python
module_name = 'seven_eval'

# Os arquivos fonte em C que precisam ser compilados
source_files = [
    os.path.join('seven_eval_lib', 'seven_eval.c')
]

# Define o módulo de extensão para a compilação
extension_mod = Extension(
    module_name,
    sources=source_files,
    include_dirs=[os.path.join(os.getcwd(), 'seven_eval_lib')]
)

# Roda a função de setup para compilar
setup(
    name=module_name,
    version='1.0',
    description='Compila a biblioteca SevenEval para uso em Python.',
    ext_modules=[extension_mod]
)

print("\n\nCompilação concluída!")
print("Verifique se um novo arquivo 'seven_eval' com a extensão .pyd ou .so foi criado.")