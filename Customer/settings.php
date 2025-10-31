<?php
require_once __DIR__ . '/../app.php';

$title = 'Paramètres';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-gear"></i>
            </div>
            <h1 class="h3 mb-3">Paramètres</h1>
            <p class="text-muted mb-3">Configurez les alertes, les préférences d'affichage et les sections épinglées. Le module de personnalisation arrive très bientôt.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/home.php') ?>">Retour à l'accueil</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
