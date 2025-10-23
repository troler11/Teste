from flask import Flask, render_template_string, request, jsonify
import requests
import pandas as pd
import time
import ast
from http.client import IncompleteRead  # ✅ para tratar erro específico

app = Flask(__name__)

# URLs da API e planilhas
url = "https://abmbus.com.br:8181/api/dashboard/mongo/95?naoVerificadas=false&agrupamentos="
headers = {
    "Accept": "application/json, text/plain, */*",
    "Authorization": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJtaW1vQGFibXByb3RlZ2UuY29tLmJyIiwiZXhwIjoxODYwNzEwOTEyfQ.2yLysK8kK1jwmSCYJODCvWgppg8WtjuLxCwxyLnm2S0qAzSp12bFVmhwhVe8pDSWWCqYBCXuj0o2wQLNtHFpRw"
}

# Planilhas
SHEET_XLSX_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6ZbME4_rlLzq-pAuslL6_kja3FWMPpBdFl2_C82Y01twcn9QX_IWwUlaNNVNRW20E5aANFU6UDw3_/pub?output=xlsx"
LINHAS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ-jeDXdqfWvVcRQL-aPgyeLstQxwRU0gQnVfzEDfU476vmHcPTaFKqJkdf6NjFEeyRW_TGotfGbodG/pub?gid=0&single=true&output=csv"
CARROS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTlOLnEeXNsgsK2uK0-hHwVhiaE6lsYUMdUE4cxJ5cVSq1YnuEtbJekwd1MS-lP1Gvybn8CYSuyuXIm/pub?gid=0&single=true&output=csv"


@app.route('/trocar_veiculo', methods=['POST'])
def trocar_veiculo():
    try:
        id_veiculo = request.json.get("idVeiculo")
        id_linha = request.json.get("linhas")
        data_inicial = request.json.get("dataInicial")
        data_final = request.json.get("dataFinal")

        if isinstance(id_linha, str):
            id_linha = ast.literal_eval(id_linha)

        payload = {
            "idVeiculo": id_veiculo,
            "linhas": id_linha,
            "dataInicial": data_inicial,
            "dataFinal": data_final
        }

        api_url = "https://abmbus.com.br:8181/api/linha/trocarveiculos"
        api_headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": headers["Authorization"],
            "Content-Type": "application/json"
        }

        response = requests.post(api_url, headers=api_headers, json=payload)
        response.raise_for_status()

        try:
            resp_json = response.json()
        except:
            resp_json = response.text

        return jsonify({"status": "sucesso", "resposta": resp_json})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route('/')
def index():
    nome_aba = time.strftime("%d%m%Y")
    print(f"\n📘 Lendo a aba da planilha: {nome_aba}")

    # 🔁 Tenta carregar planilhas até 3 vezes se ocorrer IncompleteRead
    tentativas = 3
    for tentativa in range(tentativas):
        try:
            df_sheet = pd.read_excel(SHEET_XLSX_URL, sheet_name=nome_aba)
            df_linhas = pd.read_csv(LINHAS_CSV_URL)
            df_carros = pd.read_csv(CARROS_CSV_URL)
            print(f"✅ Aba '{nome_aba}' carregada com sucesso! Linhas lidas: {len(df_sheet)}")
            break
        except IncompleteRead as e:
            print(f"⚠️ Erro IncompleteRead ({tentativa+1}/{tentativas}). Tentando novamente em 3s...")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Erro ao carregar planilhas: {e}")
            html_erro = f"""
            <html><body style='text-align:center;padding:50px;'>
            <h2 style='color:red;'>Erro ao carregar planilhas:</h2>
            <p>{e}</p>
            <p>Tentando novamente em 5 segundos...</p>
            <script>
                setTimeout(function() {{
                    location.reload();
                }}, 5000);
            </script>
            </body></html>
            """
            return html_erro
    else:
        return """
        <html><body style='text-align:center;padding:50px;'>
        <h2 style='color:red;'>Erro ao carregar planilhas: IncompleteRead</h2>
        <p>Recarregando automaticamente em 5 segundos...</p>
        <script>setTimeout(function(){ location.reload(); }, 5000);</script>
        </body></html>
        """

    # --------------------------------------
    # Funções auxiliares
    # --------------------------------------
    def obter_veiculo_escala(codLinha):
        try:
            codLinha = str(codLinha).strip()
            for _, linha_sheet in df_sheet.iterrows():
                valor_coluna_D = str(linha_sheet.iloc[3]).strip()
                linha_linhas = df_linhas[df_linhas.iloc[:, 0].astype(str).str.strip() == valor_coluna_D]
                if not linha_linhas.empty:
                    valor_coluna_B = str(linha_linhas.iloc[0, 1]).strip()
                    if valor_coluna_B == codLinha:
                        valor_coluna_G = linha_sheet.iloc[6] if not pd.isna(linha_sheet.iloc[6]) else linha_sheet.iloc[5]
                        if isinstance(valor_coluna_G, float) and valor_coluna_G.is_integer():
                            valor_coluna_G = int(valor_coluna_G)
                        return str(valor_coluna_G).strip()
            return "ZZZ-8888"
        except Exception as e:
            print(f"⚠️ Erro em obter_veiculo_escala: {e}")
            return "ZZZ-8888"

    def obter_codigo_veiculo(veiculo_escala):
        try:
            veiculo_escala = str(veiculo_escala).strip()
            linha_carro = df_carros[df_carros.iloc[:, 0].astype(str).str.strip() == veiculo_escala]
            if linha_carro.empty:
                return "ZZZ-8888"
            return str(linha_carro.iloc[0, 1]).strip()
        except:
            return "ZZZ-8888"

    def obter_coluna_c_carro(veiculo_escala):
        try:
            veiculo_escala = str(veiculo_escala).strip()
            linha_carro = df_carros[df_carros.iloc[:, 0].astype(str).str.strip() == veiculo_escala]
            if linha_carro.empty:
                return "ZZZ-8888"
            return str(linha_carro.iloc[0, 2]).strip()
        except:
            return "ZZZ-8888"

    # --------------------------------------
    # Buscar dados da API
    # --------------------------------------
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Erro ao buscar dados da API: {e}")
        return f"Erro ao buscar dados: {e}"

    # --------------------------------------
    # Processar linhas
    # --------------------------------------
    linhas_andamento = data.get("linhasAndamento", [])
    linhas_desligado = data.get("linhasCarroDesligado", [])
    linhas_sem_ponto = data.get("linhasComecaramSemPrimeiroPonto", [])
    todas_linhas = []

    for l in linhas_andamento + linhas_desligado + linhas_sem_ponto:
        if l in linhas_desligado:
            categoria = "Carro desligado"
        elif l in linhas_sem_ponto:
            categoria = "Começou sem ponto"
        else:
            categoria = "Em andamento"

        l["categoria"] = categoria
        codLinha = l.get("codLinha", None)
        veiculo_escala = obter_veiculo_escala(codLinha)
        l["veiculo_escala"] = veiculo_escala
        l["codigo_veiculo"] = obter_codigo_veiculo(veiculo_escala)
        l["coluna_c_carro"] = obter_coluna_c_carro(veiculo_escala)
        todas_linhas.append(l)

    # --------------------------------------
    # HTML da página
    # --------------------------------------
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard ABM Bus</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <style>
            body { padding: 20px; }
            th, td { text-align: center; vertical-align: middle; }
            .Em_andamento { background-color: #d1e7dd; }
            .Carro_desligado { background-color: #f8d7da; }
            .Comecou_sem_ponto { background-color: #fff3cd; }
        </style>
    </head>
    <body>
        <h2 class="mb-4">Dashboard ABM Bus</h2>
        <table class="table table-bordered table-hover">
            <thead class="table-dark">
                <tr>
                    <th>Categoria</th>
                    <th>Empresa</th>
                    <th>Linha</th>
                    <th>Cod</th>
                    <th>Código</th>
                    <th>Veículo</th>
                    <th>Veículo Escala</th>
                    <th>Status</th>
                    <th>Motorista</th>
                    <th>Codigo Veiculo</th>
                    <th>Trocar Veículo</th>
                </tr>
            </thead>
            <tbody>
                {% for linha in todas_linhas %}
                <tr class="{{ linha['categoria'].replace(' ', '_') }}" data-idrelatorio="{{ linha.get('idRelatorio', '') }}">
                    <td>{{ linha['categoria'] }}</td>
                    <td>{{ linha.get('empresa', {}).get('nome', 'N/D') }}</td>
                    <td>{{ linha.get('descricaoLinha', 'N/D') }}</td>
                    <td>{{ linha.get('idLinha', 'N/D') }}</td>
                    <td>{{ linha.get('codLinha', 'N/D') }}</td>
                    <td>{{ linha.get('veiculo', {}).get('veiculo', 'ZZZ-8888') }}</td>
                    <td><strong>{{ linha.get('veiculo_escala', 'ZZZ-8888') }}</strong></td>
                    <td>{{ linha['categoria'] }}</td>
                    <td>{{ linha.get('nome', 'DESCONHECIDO') }}</td>
                    <td><strong>{{ linha.get('codigo_veiculo', 'ZZZ-8888') }}</strong></td>
                    <td>
                        <button class="btn btn-primary btn-sm trocar-btn" 
                                data-idveiculo="{{ linha.get('codigo_veiculo', '') }}" 
                                data-idlinha="[{{ linha.get('idLinha', '') }}]"
                                data-veiculoc="{{ linha.get('coluna_c_carro', 'ZZZ-8888') }}"
                                data-idrelatorio="{{ linha.get('idRelatorio', '') }}">
                            Trocar
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <script>
        $(document).ready(function() {
            function trocarAutomaticamente() {
                $("tbody tr").each(function() {
                    var veiculoAtual = $(this).find("td:nth-child(6)").text().trim(); 
                    var veiculoCorreto = $(this).find(".trocar-btn").data("veiculoc").toString().trim(); 
                    var idVeiculo = $(this).find(".trocar-btn").data("idveiculo");
                    var idLinha = $(this).find(".trocar-btn").data("idlinha");
                    var idRelatorio = $(this).data("idrelatorio");

                    if (veiculoAtual !== veiculoCorreto) {
                        console.log("🚀 Diferença encontrada:", veiculoAtual, "→", veiculoCorreto);

                        if (typeof idLinha === "string") {
                            idLinha = idLinha.replace(/[\\[\\]]/g, '').split(',').map(Number);
                        }

                        var hoje = new Date();
                        var dia = String(hoje.getDate()).padStart(2, '0');
                        var mes = String(hoje.getMonth() + 1).padStart(2, '0');
                        var ano = hoje.getFullYear();
                        var dataAtual = dia + '/' + mes + '/' + ano;

                        $.ajax({
                            url: "/trocar_veiculo",
                            type: "POST",
                            contentType: "application/json",
                            data: JSON.stringify({
                                idVeiculo: idVeiculo,
                                linhas: idLinha,
                                dataInicial: dataAtual,
                                dataFinal: dataAtual
                            }),
                            success: function(res) {
                                console.log("✅ Veículo trocado automaticamente:", veiculoAtual, "→", veiculoCorreto);

                                if(idRelatorio) {
                                    $.ajax({
                                        url: "https://abmbus.com.br:8181/api/linha/marca_relatorio_alterado?id=" + idRelatorio + "&alterado=true",
                                        type: "POST",
                                        headers: {
                                            "Accept": "application/json, text/plain, */*",
                                            "Authorization": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJtaW1vQGFibXByb3RlZ2UuY29tLmJyIiwiZXhwIjoxODYwOTcyMDUxfQ.G7jddb2Zcmc-7tTlaF0D6ROD6qlytXHs52DoebPaQvFA8VCuk8rMNUE3r1ywBdDnP1JbnzfbGQpseKiOVwbq2Q"
                                        },
                                        success: function(resp) {
                                            console.log("📌 Relatório marcado como alterado:", idRelatorio);
                                        },
                                        error: function(err) {
                                            console.error("❌ Erro ao marcar relatório:", idRelatorio, err);
                                        }
                                    });
                                }
                            },
                            error: function(err) {
                                console.error("❌ Erro ao trocar veículo:", veiculoAtual, err);
                            }
                        });
                    } else {
                        console.log("✅ Veículos iguais, sem troca:", veiculoAtual, "==", veiculoCorreto);
                    }
                });
            }

            trocarAutomaticamente();
            setInterval(function() {
                location.reload();
            }, 180000); 
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(html, todas_linhas=todas_linhas)

if __name__ == "__main__":
    # Executa o servidor Flask em todas as interfaces de rede
    app.run(host="0.0.0.0", port=80, debug=True)

