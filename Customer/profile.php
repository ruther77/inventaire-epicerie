<?php
require_once __DIR__ . '/../app.php';

$title = 'Profil';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-person-circle"></i>
            </div>
            <h1 class="h3 mb-3">Profil</h1>
            <p class="text-muted mb-3">Personnalisez vos informations et vos préférences. Nous finalisons cet espace pour vous offrir un suivi précis de vos données.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/settings.php') ?>">Accéder aux paramètres</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
