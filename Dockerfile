# Usar a imagem oficial do Playwright que já inclui navegadores e dependências do sistema.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiar o arquivo de dependências para o contêiner
COPY requirements.txt .

# Instalar as dependências Python e as dependências do Playwright
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps

# Copiar o resto dos arquivos da aplicação para o contêiner
COPY . .

# Tornar o script de entrypoint executável
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Definir o entrypoint que será executado quando o contêiner iniciar
ENTRYPOINT ["/entrypoint.sh"]
