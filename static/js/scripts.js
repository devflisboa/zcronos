document.addEventListener('DOMContentLoaded', function() {
    // Função para validar o formulário de abastecimento e despesa
    function validarFormulario(form) {
        let camposObrigatorios = form.querySelectorAll('[required]');
        let formValido = true;

        camposObrigatorios.forEach(function(campo) {
            if (!campo.value.trim()) {
                campo.classList.add('is-invalid');
                formValido = false;
            } else {
                campo.classList.remove('is-invalid');
            }
        });

        if (!formValido) {
            alert("Por favor, preencha todos os campos obrigatórios.");
        }
        return formValido;
    }



    // Função para gerar o gráfico de ganhos
    function gerarGraficoGanhos(labels, dataGanhosBrutos) {
        var ctx = document.getElementById('grafico_ganhos').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ganhos Brutos',
                    data: dataGanhosBrutos,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Inicializar o gráfico de ganhos
    const labels = JSON.parse(document.getElementById('labels').textContent);
    const dataGanhosBrutos = JSON.parse(document.getElementById('data_ganhos_brutos').textContent);
    gerarGraficoGanhos(labels, dataGanhosBrutos);
});

function formatCurrency(value) {
    return value.toLocaleString('pt-BR', { 
        style: 'currency', 
        currency: 'BRL' 
    });
}

