fetch('impactos_ml.json')
  .then(response => response.json())
  .then(data => {
    // Atualiza os indicadores de pedidos válidos
    document.getElementById('pedidos-validos').innerText = data.resumo_validacao.total_pedidos_validos;
    
    // Exemplo de iteração sobre motivos de reclamação
    console.log("Motivos:", data.motivos_reclamacao);
    console.log("Transportadoras:", data.transportadoras);
    console.log("Top SKUs:", data.skus_produtos_impactados);
  });
