#!/bin/bash

# Loop infinito para executar o script periodicamente
while true
do
  echo "-------------------------------------------"
  echo "Iniciando a execução do script de extração..."
  echo "Data e Hora: $(date)"
  echo "-------------------------------------------"
  
  # Executa o script python
  python app.py
  
  echo "-------------------------------------------"
  echo "Execução concluída."
  echo "Aguardando 6 horas para a próxima execução..."
  echo "-------------------------------------------"
  
  # Aguarda 6 horas (21600 segundos)
  sleep 21600
done
