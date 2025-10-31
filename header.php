<?php
require_once __DIR__ . '/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/categorie.php';

$customerTitle = $title ?? 'JELLOULI';
$categoryList = Categorie::afficher();

$badgeCycle = [
    ['label' => 'Top ventes', 'class' => 'badge-top'],
    ['label' => 'Promo', 'class' => 'badge-promo'],
    ['label' => 'Nouveau', 'class' => 'badge-new'],
];

$quickFilters = array_slice(array_map(static function ($category) {
    return [
        'label' => $category->get('n'),
        'url' => url_for('Customer/shop.php?id=' . urlencode($category->get('n'))),
    ];
}, $categoryList), 0, 6);

$cartCount = isset($_SESSION['cart_items']) && is_array($_SESSION['cart_items']) ? count($_SESSION['cart_items']) : 0;
$wishlistCount = isset($_SESSION['wishlist']) && is_array($_SESSION['wishlist']) ? count($_SESSION['wishlist']) : 0;

$quickActions = [
    [
        'label' => 'Explorer la boutique',
        'description' => 'Parcourez toutes les catégories et trouvez l\'article parfait.',
        'icon' => 'bi-grid',
        'url' => url_for('Customer/shop.php'),
        'badge' => 'Catalogue',
    ],
    [
        'label' => 'Suivre mes commandes',
        'description' => 'Consultez vos suivis, factures et confirmations.',
        'icon' => 'bi-receipt-cutoff',
        'url' => url_for('Customer/orders.php'),
        'badge' => 'Historique',
    ],
    [
        'label' => 'Gérer mon panier',
        'description' => 'Ajustez vos articles avant de passer commande.',
        'icon' => 'bi-bag',
        'url' => url_for('Customer/cart.php'),
        'badge' => 'Panier',
    ],
    [
        'label' => 'Mes favoris',
        'description' => 'Retrouvez vos produits enregistrés en un instant.',
        'icon' => 'bi-heart',
        'url' => url_for('Customer/favorites.php'),
        'badge' => 'Favoris',
    ],
    [
        'label' => 'Promotions en cours',
        'description' => 'Accédez directement aux offres limitées.',
        'icon' => 'bi-lightning-charge',
        'url' => url_for('Customer/shop.php?promo=1'),
        'badge' => 'Promo',
    ],
    [
        'label' => 'Centre de contrôle',
        'description' => 'Pilotez inventaire, commandes et analyses internes.',
        'icon' => 'bi-kanban',
        'url' => url_for('Customer/dashboard.php'),
        'badge' => 'Equipe',
    ],
];

$utilityLinks = [
    [
        'label' => 'Profil',
        'icon' => 'bi-person-circle',
        'url' => url_for('Customer/profile.php'),
    ],
    [
        'label' => 'Paramètres',
        'icon' => 'bi-gear',
        'url' => url_for('Customer/settings.php'),
    ],
    [
        'label' => 'Assistance',
        'icon' => 'bi-question-circle',
        'url' => url_for('Customer/support.php'),
    ],
    [
        'label' => 'Déconnexion',
        'icon' => 'bi-box-arrow-right',
        'url' => url_for('Customer/logout.php'),
    ],
];
?>
<!DOCTYPE html>
<html lang="fr">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($customerTitle, ENT_QUOTES, 'UTF-8') ?> - JELLOULI</title>

    <link rel="stylesheet" href="<?= asset('assets/css/main/app.css') ?>">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.svg') ?>" type="image/x-icon">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.png') ?>" type="image/png">
    <link rel="stylesheet" href="<?= asset('Customer/style.css') ?>">

    <link rel="stylesheet" href="<?= asset('assets/css/shared/iconly.css') ?>">
    <script defer src="<?= asset('Customer/navigation.js') ?>"></script>
</head>

<body>
    <div id="app" class="app-shell">
        <div id="main" class="layout-horizontal">
            <header class="workspace-header mb-5">
                <div class="container">
                    <div class="workspace-header__bar">
                        <div class="workspace-header__group workspace-header__group--left">
                            <button class="workspace-header__burger d-inline-flex d-lg-none align-items-center justify-content-center" type="button" aria-expanded="false" aria-controls="workspacePanel" data-workspace-toggle>
                                <span class="visually-hidden">Ouvrir le menu</span>
                                <i class="bi bi-list"></i>
                            </button>
                            <a class="workspace-header__logo" href="<?= url_for('Customer/home.php') ?>">
                                <img src="<?= asset('assets/images/logo/logo-jell.png') ?>" height="30" alt="Logo Jellouli">
                            </a>
                            <button class="workspace-header__switch d-none d-lg-inline-flex align-items-center" type="button" aria-expanded="false" aria-controls="workspacePanel" data-workspace-toggle>
                                <i class="bi bi-layout-text-sidebar-reverse me-2"></i>
                                Espace navigation
                            </button>
                        </div>
                        <button class="workspace-command" type="button" data-search-toggle aria-expanded="false" aria-controls="globalSearch">
                            <i class="bi bi-search me-2"></i>
                            <span>Rechercher un produit, une action ou une page</span>
                            <span class="workspace-command__shortcut">Ctrl + K</span>
                        </button>
                        <div class="workspace-header__group workspace-header__group--right">
                            <nav class="workspace-status d-none d-md-flex" aria-label="Accès rapides">
                                <a class="status-chip" href="<?= url_for('Customer/cart.php') ?>">
                                    <i class="bi bi-bag me-1"></i>
                                    <span>Panier</span>
                                    <span class="status-chip__count" data-cart-count><?= $cartCount ?></span>
                                </a>
                                <a class="status-chip" href="<?= url_for('Customer/favorites.php') ?>">
                                    <i class="bi bi-heart me-1"></i>
                                    <span>Favoris</span>
                                    <span class="status-chip__count" data-wishlist-count><?= $wishlistCount ?></span>
                                </a>
                                <a class="status-chip" href="<?= url_for('Customer/orders.php') ?>">
                                    <i class="bi bi-receipt-cutoff me-1"></i>
                                    <span>Commandes</span>
                                </a>
                            </nav>
                            <div class="dropdown">
                                <button class="workspace-avatar btn btn-icon d-flex align-items-center" id="userUtilities" data-bs-toggle="dropdown" aria-expanded="false">
                                    <span class="workspace-avatar__bell position-relative me-2">
                                        <i class="bi bi-bell"></i>
                                        <span class="badge rounded-pill bg-danger notification-dot" data-notification-indicator></span>
                                    </span>
                                    <div class="avatar avatar-md2">
                                        <img src="<?= asset('assets/images/faces/1.jpg') ?>" alt="Avatar client">
                                    </div>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end shadow-lg" aria-labelledby="userUtilities">
                                    <li class="dropdown-header text-muted text-uppercase">Zone rapide</li>
                                    <li>
                                        <a class="dropdown-item d-flex justify-content-between align-items-center" href="<?= url_for('Customer/cart.php') ?>">
                                            <span><i class="bi bi-bag me-2"></i>Panier</span>
                                            <span class="badge bg-primary rounded-pill" data-cart-count><?= $cartCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item d-flex justify-content-between align-items-center" href="<?= url_for('Customer/favorites.php') ?>">
                                            <span><i class="bi bi-heart me-2"></i>Favoris</span>
                                            <span class="badge bg-danger rounded-pill" data-wishlist-count><?= $wishlistCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/orders.php') ?>"><i class="bi bi-receipt-cutoff me-2"></i>Commandes</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/dashboard.php') ?>"><i class="bi bi-kanban me-2"></i>Centre de contrôle</a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li class="dropdown-header text-muted text-uppercase">Mon compte</li>
                                    <?php foreach ($utilityLinks as $link): ?>
                                        <li>
                                            <a class="dropdown-item" href="<?= $link['url'] ?>"><i class="bi <?= $link['icon'] ?> me-2"></i><?= htmlspecialchars($link['label'], ENT_QUOTES, 'UTF-8') ?></a>
                                        </li>
                                    <?php endforeach; ?>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="workspace-header__summary">
                    <div class="container">
                        <div class="workspace-summary" data-pinned-summary></div>
                    </div>
                </div>
                <aside class="workspace-drawer" id="workspacePanel" data-workspace-panel aria-hidden="true">
                    <div class="workspace-drawer__inner">
                        <div class="workspace-drawer__header">
                            <div>
                                <span class="workspace-drawer__eyebrow">Navigation unifiée</span>
                                <h2 class="workspace-drawer__title">Choisissez votre prochaine action</h2>
                                <p class="text-muted mb-0">Retrouvez vos parcours clients et outils internes sans multiplier les onglets.</p>
                            </div>
                            <button class="btn btn-link text-decoration-none" type="button" data-workspace-toggle>
                                <i class="bi bi-x-lg me-1"></i>Fermer
                            </button>
                        </div>
                        <section class="workspace-drawer__section">
                            <h3 class="workspace-drawer__section-title">Parcours rapides</h3>
                            <div class="workspace-drawer__grid">
                                <?php foreach ($quickActions as $action): ?>
                                    <a class="workspace-card" href="<?= $action['url'] ?>">
                                        <span class="workspace-card__icon"><i class="bi <?= $action['icon'] ?>"></i></span>
                                        <div class="workspace-card__content">
                                            <span class="workspace-card__label"><?= htmlspecialchars($action['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                            <p class="workspace-card__desc mb-0"><?= htmlspecialchars($action['description'], ENT_QUOTES, 'UTF-8') ?></p>
                                        </div>
                                        <span class="workspace-card__badge"><?= htmlspecialchars($action['badge'], ENT_QUOTES, 'UTF-8') ?></span>
                                    </a>
                                <?php endforeach; ?>
                            </div>
                        </section>
                        <section class="workspace-drawer__section" data-pinned-container>
                            <div class="workspace-drawer__section-header">
                                <h3 class="workspace-drawer__section-title">Sections épinglées</h3>
                                <button class="btn btn-link btn-sm text-decoration-none" type="button" data-clear-pins>
                                    <i class="bi bi-x-circle me-1"></i>Effacer
                                </button>
                            </div>
                            <p class="text-muted small" data-empty-message>Aucune section épinglée pour le moment.</p>
                            <div class="workspace-pinned row g-3" data-pinned-list></div>
                        </section>
                        <section class="workspace-drawer__section">
                            <div class="workspace-drawer__section-header">
                                <h3 class="workspace-drawer__section-title">Catalogue par catégories</h3>
                                <div class="workspace-drawer__chips">
                                    <?php foreach ($quickFilters as $filter): ?>
                                        <a class="workspace-chip" href="<?= $filter['url'] ?>">
                                            <i class="bi bi-funnel me-1"></i><?= htmlspecialchars($filter['label'], ENT_QUOTES, 'UTF-8') ?>
                                        </a>
                                    <?php endforeach; ?>
                                </div>
                            </div>
                            <div class="workspace-drawer__grid workspace-drawer__grid--compact">
                                <?php foreach ($categoryList as $index => $cat): ?>
                                    <?php
                                        $categoryName = $cat->get('n');
                                        $categoryUrl = url_for('Customer/shop.php?id=' . urlencode($categoryName));
                                        $badge = $badgeCycle[$index % count($badgeCycle)];
                                    ?>
                                    <article class="workspace-category" data-category-card data-category-name="<?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>" data-category-url="<?= htmlspecialchars($categoryUrl, ENT_QUOTES, 'UTF-8') ?>">
                                        <div class="workspace-category__content">
                                            <a class="workspace-category__link stretched-link" href="<?= $categoryUrl ?>">
                                                <?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>
                                            </a>
                                            <p class="workspace-category__hint">Découvrez nouveautés, promotions et top ventes de cette famille.</p>
                                        </div>
                                        <div class="workspace-category__footer">
                                            <span class="badge <?= htmlspecialchars($badge['class'], ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($badge['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                            <div class="workspace-category__actions">
                                                <a class="btn btn-sm btn-outline-primary" href="<?= $categoryUrl ?>">Ouvrir</a>
                                                <button class="btn btn-sm btn-outline-secondary" type="button" data-pin-toggle>
                                                    <i class="bi bi-pin-angle"></i>
                                                    <span class="ms-1">Épingler</span>
                                                </button>
                                            </div>
                                        </div>
                                    </article>
                                <?php endforeach; ?>
                            </div>
                        </section>
                        <section class="workspace-drawer__section">
                            <h3 class="workspace-drawer__section-title">Utilitaires</h3>
                            <div class="workspace-drawer__links">
                                <a class="workspace-link" href="<?= url_for('Customer/home.php') ?>"><i class="bi bi-house-door me-2"></i>Accueil client</a>
                                <a class="workspace-link" href="<?= url_for('Customer/dashboard.php') ?>"><i class="bi bi-kanban me-2"></i>Tableau de bord interne</a>
                                <a class="workspace-link" href="<?= url_for('Customer/orders.php') ?>"><i class="bi bi-receipt-cutoff me-2"></i>Commandes et factures</a>
                                <a class="workspace-link" href="<?= url_for('Customer/cart.php') ?>"><i class="bi bi-bag me-2"></i>Panier</a>
                                <a class="workspace-link" href="<?= url_for('Customer/favorites.php') ?>"><i class="bi bi-heart me-2"></i>Favoris</a>
                                <a class="workspace-link" href="<?= url_for('Customer/settings.php') ?>"><i class="bi bi-gear me-2"></i>Préférences</a>
                                <a class="workspace-link" href="<?= url_for('Customer/support.php') ?>"><i class="bi bi-question-circle me-2"></i>Support &amp; aide</a>
                                <a class="workspace-link" href="<?= url_for('Customer/logout.php') ?>"><i class="bi bi-box-arrow-right me-2"></i>Déconnexion</a>
                            </div>
                        </section>
                    </div>
                </aside>
                <div class="workspace-backdrop" data-workspace-backdrop></div>
                <div class="global-search-overlay" id="globalSearch" data-global-search aria-hidden="true">
                    <div class="global-search-overlay__inner container">
                        <div class="global-search-overlay__header">
                            <div>
                                <h2 class="h4 mb-1">Rechercher ou lancer une action</h2>
                                <p class="text-muted mb-0">Produits, catégories, commandes ou pages d'administration.</p>
                            </div>
                            <button class="btn btn-link text-decoration-none" type="button" data-search-toggle>
                                <i class="bi bi-x-lg me-1"></i>
                                Fermer
                            </button>
                        </div>
                        <form class="global-search-form" action="<?= url_for('Customer/shop.php') ?>" method="get" data-global-search-form>
                            <label class="visually-hidden" for="globalSearchInput">Recherche globale</label>
                            <div class="input-group input-group-lg">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input id="globalSearchInput" class="form-control" type="search" name="q" placeholder="Rechercher un produit, une marque ou une promotion" autocomplete="off" data-global-search-input>
                                <button class="btn btn-primary" type="submit">Rechercher</button>
                            </div>
                        </form>
                        <div class="global-search-actions">
                            <button class="btn btn-link px-0" type="button" data-save-search>
                                <i class="bi bi-bookmark-plus me-1"></i>Enregistrer cette recherche
                            </button>
                            <button class="btn btn-link text-danger px-0" type="button" data-clear-searches>
                                <i class="bi bi-trash me-1"></i>Effacer les recherches enregistrées
                            </button>
                        </div>
                        <div class="global-search-saved">
                            <h3 class="h6 mb-2">Recherches enregistrées</h3>
                            <div class="saved-search-chips" data-saved-searches data-placeholder="false"></div>
                            <p class="text-muted small" data-no-saved-search>Aucune recherche enregistrée pour le moment.</p>
                        </div>
                    </div>
                </div>
            </header>
