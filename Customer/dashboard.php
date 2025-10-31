<?php
require_once __DIR__ . '/../app.php';

$title = 'Centre de contrôle';
$inventorySnapshot = [
    'active_products' => 1245,
    'low_stock' => 28,
    'incoming_shipments' => 6,
];

$orderSnapshot = [
    'today' => 86,
    'processing' => 42,
    'fulfilled' => 312,
];

$alerts = [
    ['label' => 'Inventaire', 'message' => '28 références sous le seuil critique', 'type' => 'warning'],
    ['label' => 'Commandes', 'message' => '5 commandes en attente de validation', 'type' => 'info'],
];

$recentOrders = [
    ['ref' => 'CMD-2024-001', 'client' => 'Société Atlas', 'statut' => 'En préparation', 'date' => '18/04/2024', 'total' => 1250.40],
    ['ref' => 'CMD-2024-002', 'client' => 'Marché Central', 'statut' => 'Expédiée', 'date' => '18/04/2024', 'total' => 842.10],
    ['ref' => 'CMD-2024-003', 'client' => 'Restaurant Lagon', 'statut' => 'Facturée', 'date' => '17/04/2024', 'total' => 1563.00],
    ['ref' => 'CMD-2024-004', 'client' => 'Épicerie du Port', 'statut' => 'En attente', 'date' => '17/04/2024', 'total' => 432.75],
    ['ref' => 'CMD-2024-005', 'client' => 'Collectivité Sud', 'statut' => 'Expédiée', 'date' => '16/04/2024', 'total' => 2987.90],
];

include __DIR__ . '/../header.php';
?>

<div class="content-wrapper container">
    <div class="page-content">
        <section class="mb-4">
            <div class="row g-3 align-items-center">
                <div class="col-lg-8">
                    <h1 class="h3 mb-1">Centre de contrôle</h1>
                    <p class="text-muted mb-0">Vue d'ensemble pour vos équipes internes : inventaire, commandes et indicateurs clés.</p>
                </div>
                <div class="col-lg-4 text-lg-end">
                    <a class="btn btn-primary" href="<?= url_for('Customer/shop.php') ?>"><i class="bi bi-plus-lg me-2"></i>Créer une commande rapide</a>
                </div>
            </div>
        </section>

        <section class="dashboard-grid">
            <article class="dashboard-card">
                <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h5 mb-0">Inventaire</h2>
                    <span class="badge bg-light text-dark">Temps réel</span>
                </div>
                <div class="dashboard-card__value"><?= number_format($inventorySnapshot['active_products'], 0, '', ' ') ?></div>
                <p class="text-muted mb-2">Références actives</p>
                <div class="dashboard-progress"><span style="width: 74%"></span></div>
                <ul class="list-unstyled mb-0 text-muted small">
                    <li><i class="bi bi-arrow-down-right text-danger me-2"></i><?= $inventorySnapshot['low_stock'] ?> articles à surveiller</li>
                    <li><i class="bi bi-truck me-2 text-success"></i><?= $inventorySnapshot['incoming_shipments'] ?> réapprovisionnements attendus</li>
                </ul>
            </article>

            <article class="dashboard-card">
                <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h5 mb-0">Commandes</h2>
                    <span class="badge bg-primary">Aujourd'hui</span>
                </div>
                <div class="dashboard-card__value"><?= number_format($orderSnapshot['today'], 0, '', ' ') ?></div>
                <p class="text-muted mb-2">Commandes reçues</p>
                <div class="dashboard-progress"><span style="width: 58%"></span></div>
                <ul class="list-unstyled mb-0 text-muted small">
                    <li><i class="bi bi-hourglass-split me-2 text-warning"></i><?= $orderSnapshot['processing'] ?> en préparation</li>
                    <li><i class="bi bi-check-circle me-2 text-success"></i><?= $orderSnapshot['fulfilled'] ?> expédiées cette semaine</li>
                </ul>
            </article>

            <article class="dashboard-card">
                <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h5 mb-0">Analyses</h2>
                    <span class="badge bg-success">+12%</span>
                </div>
                <div class="dashboard-card__value">1,8 M€</div>
                <p class="text-muted mb-2">CA glissant 30 jours</p>
                <div class="dashboard-progress"><span style="width: 82%"></span></div>
                <ul class="list-unstyled mb-0 text-muted small">
                    <li><i class="bi bi-graph-up-arrow me-2 text-success"></i>Croissance soutenue sur les promotions</li>
                    <li><i class="bi bi-people me-2 text-primary"></i>Les commandes pro représentent 38% du volume</li>
                </ul>
            </article>
        </section>

        <section class="row g-4 mt-1">
            <div class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-body">
                        <h2 class="h5 mb-3">Alertes</h2>
                        <?php foreach ($alerts as $alert): ?>
                            <div class="d-flex align-items-start mb-3">
                                <span class="badge rounded-pill <?= $alert['type'] === 'warning' ? 'bg-warning text-dark' : 'bg-info text-dark' ?> me-3"><?= htmlspecialchars($alert['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                <p class="mb-0 text-muted"><?= htmlspecialchars($alert['message'], ENT_QUOTES, 'UTF-8') ?></p>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h2 class="h5 mb-0">Actions rapides</h2>
                            <a class="btn btn-sm btn-outline-primary" href="<?= url_for('Customer/settings.php') ?>">Personnaliser</a>
                        </div>
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item"><i class="bi bi-pin-angle me-2 text-primary"></i>Configurer les catégories épinglées pour l'équipe logistique</li>
                            <li class="list-group-item"><i class="bi bi-clock-history me-2 text-success"></i>Planifier un réassort automatique sur les produits critiques</li>
                            <li class="list-group-item"><i class="bi bi-bell me-2 text-warning"></i>Activer les notifications quotidiennes pour les ruptures potentielles</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

        <section class="card shadow-sm mt-4">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h2 class="h5 mb-0">Dernières commandes</h2>
                    <a class="btn btn-sm btn-outline-secondary" href="<?= url_for('Customer/orders.php') ?>">Voir toutes les commandes</a>
                </div>
                <div class="table-responsive">
                    <table class="table align-middle mb-0">
                        <thead>
                            <tr>
                                <th>Référence</th>
                                <th>Client</th>
                                <th>Statut</th>
                                <th>Date</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($recentOrders as $order): ?>
                                <tr>
                                    <td><?= htmlspecialchars($order['ref'], ENT_QUOTES, 'UTF-8') ?></td>
                                    <td><?= htmlspecialchars($order['client'], ENT_QUOTES, 'UTF-8') ?></td>
                                    <td><span class="badge bg-light text-dark"><?= htmlspecialchars($order['statut'], ENT_QUOTES, 'UTF-8') ?></span></td>
                                    <td><?= htmlspecialchars($order['date'], ENT_QUOTES, 'UTF-8') ?></td>
                                    <td><?= number_format((float) $order['total'], 2, '.', ' ') ?> Dhs</td>
                                </tr>
                            <?php endforeach; ?>
                            <?php if (empty($recentOrders)): ?>
                                <tr>
                                    <td colspan="5" class="text-center text-muted">Aucune commande récente</td>
                                </tr>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    </div>

    <?php include __DIR__ . '/footer.php'; ?>
