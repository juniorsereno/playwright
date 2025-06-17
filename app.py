import time
import csv
import os
from playwright.sync_api import sync_playwright, expect

# --- CONFIGURAÇÕES ---
URL_AIRBNB = "https://www.airbnb.com.br/rooms/673651674777082764"
NUMERO_DE_CALENDARIOS_A_PROCESSAR = 6 # Cada "processamento" avança 2 meses. 6 processamentos = 12 meses.
                                     # O primeiro processamento pega os 2 meses iniciais.
                                     # As 5 processamentos seguintes avançam 5x2=10 meses, totalizando 12 meses.
OUTPUT_CSV_FILE = "/app/data/disponibilidade_airbnb.csv" # Caminho dentro do container

def parse_month_year_from_header(header_text):
    """Converte 'janeiro de 2026' para ('janeiro', 1, 2026)."""
    parts = header_text.lower().split(' de ')
    month_name = parts[0].strip()
    year = int(parts[1].strip())
    
    month_map = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
    }
    month_number = month_map.get(month_name, 0) # Retorna 0 se não encontrar
    return month_name, month_number, year

def extrair_disponibilidade():
    print("Iniciando a automação no Airbnb para extração de disponibilidade...")
    all_availability_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=50) # MODIFICADO: headless=True para Docker
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()

        try:
            print(f"Acessando: {URL_AIRBNB}")
            page.goto(URL_AIRBNB, timeout=60000)

            print("Procurando por pop-up de consentimento de cookies...")
            try:
                cookie_accept_button = page.get_by_role("button", name="Aceitar todos").first
                expect(cookie_accept_button).to_be_visible(timeout=10000)
                cookie_accept_button.click()
                print("Pop-up de consentimento de cookies aceito.")
                time.sleep(2)
            except Exception:
                print("Nenhum pop-up de consentimento de cookies encontrado ou não foi possível interagir. Continuando...")

            print("Procurando por pop-up inicial para fechar...")
            try:
                fechar_popup_button = page.locator('button[aria-label="Fechar"]').first
                expect(fechar_popup_button).to_be_visible(timeout=10000)
                fechar_popup_button.click()
                print("Pop-up inicial fechado.")
            except Exception:
                print("Nenhum pop-up inicial encontrado. Continuando...")

            calendario_principal_container = page.locator('div[data-testid="inline-availability-calendar"]')
            botao_avancar = calendario_principal_container.locator('button[aria-label="Mova para frente para alternar para o próximo mês."]')

            print("Aguardando o calendário principal carregar...")
            expect(calendario_principal_container).to_be_visible(timeout=20000)
            expect(botao_avancar).to_be_visible(timeout=10000)
            print("Calendário principal carregado com sucesso.")
            
            calendario_principal_container.scroll_into_view_if_needed()
            time.sleep(1)

            for i in range(NUMERO_DE_CALENDARIOS_A_PROCESSAR):
                print(f"\nProcessando conjunto de calendários {i + 1}/{NUMERO_DE_CALENDARIOS_A_PROCESSAR}...")

                if i > 0:
                    print("Avançando para os próximos meses...")
                    botao_avancar.click()
                    time.sleep(0.5) 
                    botao_avancar.click()
                    time.sleep(1)

                visible_month_panels = calendario_principal_container.locator('div._ytfarf[data-visible="true"]')
                
                expect(visible_month_panels.first).to_be_visible(timeout=10000)
                
                count = visible_month_panels.count()
                print(f"Encontrados {count} painéis de mês visíveis.")

                for panel_index in range(min(count, 2)):
                    panel = visible_month_panels.nth(panel_index)
                    
                    try:
                        month_year_header = panel.locator('h3.hpipapi')
                        expect(month_year_header).to_be_visible(timeout=5000)
                        month_year_text = month_year_header.inner_text()
                        month_name, month_num, year_num = parse_month_year_from_header(month_year_text)
                        print(f"Processando mês: {month_name} de {year_num}")

                        day_cells = panel.locator('div[data-testid^="calendar-day-"]')
                        
                        if day_cells.count() == 0:
                            print(f"  Nenhuma célula de dia encontrada para {month_name} de {year_num}.")
                            continue

                        for day_idx in range(day_cells.count()):
                            day_cell_div = day_cells.nth(day_idx)
                            try:
                                day_text = day_cell_div.inner_text()
                                if not day_text.strip().isdigit():
                                    continue
                                day_num = int(day_text)
                                
                                is_blocked_str = day_cell_div.get_attribute('data-is-day-blocked')
                                status = "indisponível" if is_blocked_str == "true" else "disponível"
                                
                                full_date = f"{year_num}-{str(month_num).zfill(2)}-{str(day_num).zfill(2)}"
                                
                                all_availability_data.append({
                                    "DataCompleta": full_date,
                                    "Dia": day_num,
                                    "MesNome": month_name,
                                    "MesNumero": month_num,
                                    "Ano": year_num,
                                    "Status": status
                                })
                            except Exception as e_day:
                                print(f"  Erro ao processar célula do dia: {e_day}")
                                continue

                    except Exception as e_panel:
                        print(f"Erro ao processar painel do mês {panel_index + 1}: {e_panel}")
                        continue

            if all_availability_data:
                print(f"\nSalvando dados em {OUTPUT_CSV_FILE}...")
                # Garante que o diretório de saída exista
                os.makedirs(os.path.dirname(OUTPUT_CSV_FILE), exist_ok=True)
                keys = all_availability_data[0].keys()
                with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as output_file:
                    dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(all_availability_data)
                print("Dados salvos com sucesso!")
            else:
                print("Nenhum dado de disponibilidade foi extraído.")

        except Exception as e:
            print(f"\n--- OCORREU UM ERRO GERAL NA AUTOMAÇÃO ---")
            print(f"Erro: {e}")
            screenshot_path = "/app/data/erro_geral.png"
            print(f"Um erro aconteceu. Verifique o screenshot '{screenshot_path}' para ver o estado final da página.")
            page.screenshot(path=screenshot_path, full_page=True)

        finally:
            print("\nAutomação concluída. Fechando o navegador.")
            browser.close()

if __name__ == "__main__":
    extrair_disponibilidade()
