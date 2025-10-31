<?php
require_once __DIR__ . '/../config/app.php';
require_once APP_ROOT . '/Metier/produit.php';
require_once APP_ROOT . '/Metier/categorie.php';

$title = 'Shop';
$products = Produit::afficher();
$categoryList = Categorie::afficher();
$currentCategory = isset($_GET['id']) ? $_GET['id'] : null;
$searchQuery = isset($_GET['q']) ? trim((string) $_GET['q']) : '';
$contextFilters = array_map(static function ($category) {
    return $category->get('n');
}, $categoryList);

include __DIR__ . '/pages/header.php';
?>

    <script>
        const selectedCategory = new URLSearchParams(window.location.search).get('id');
    </script>

    <style>
        .not-active-prod {
            display: none;
        }
    </style>

    <div class="page-content-wrapper">
        <section class="shop-context">
            <div class="container container-wide">
                <nav aria-label="breadcrumb" class="shop-breadcrumb">
                    <ol class="breadcrumb mb-3">
                        <li class="breadcrumb-item"><a href="<?= url_for('Customer/home.php') ?>">Accueil</a></li>
                        <li class="breadcrumb-item"><a href="<?= url_for('Customer/shop.php') ?>">Boutique</a></li>
                        <?php if ($currentCategory): ?>
                            <li class="breadcrumb-item active" aria-current="page"><?= htmlspecialchars($currentCategory, ENT_QUOTES, 'UTF-8') ?></li>
                        <?php elseif ($searchQuery !== ''): ?>
                            <li class="breadcrumb-item active" aria-current="page">Recherche : <?= htmlspecialchars($searchQuery, ENT_QUOTES, 'UTF-8') ?></li>
                        <?php else: ?>
                            <li class="breadcrumb-item active" aria-current="page">Aperçu</li>
                        <?php endif; ?>
                    </ol>
                </nav>
                <div class="shop-context__header">
                    <div>
                        <h1 class="h3 mb-1">Parcourez le catalogue</h1>
                        <p class="text-muted mb-0">Affinez votre sélection grâce aux filtres contextuels : catégories, promotions ou top ventes.</p>
                    </div>
                    <div class="shop-context__pinned" data-pinned-summary></div>
                </div>
                <div class="shop-context__tabs">
                    <button class="context-tab active" type="button" data-context-tab="all">Tous</button>
                    <button class="context-tab" type="button" data-context-tab="promo">Promotions</button>
                    <button class="context-tab" type="button" data-context-tab="top">Top ventes</button>
                    <button class="context-tab" type="button" data-context-tab="new">Nouveautés</button>
                    <?php foreach ($contextFilters as $filter): ?>
                        <button class="context-tab" type="button" data-context-tab="<?= htmlspecialchars($filter, ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($filter, ENT_QUOTES, 'UTF-8') ?></button>
                    <?php endforeach; ?>
                </div>
                <div class="shop-context__saved-searches">
                    <span class="text-muted small">Recherches enregistrées</span>
                    <div class="saved-search-chips" data-saved-searches data-skip-global="true"></div>
                </div>
            </div>
        </section>
        <div class="shop-page-action-bar mb-30">
            <div class="container container-wide">
                <div class="action-bar-inner">
                    <div class="row align-items-center g-3">
                        <div class="col-12 col-lg-7">
                            <div class="shop-filter-pills" data-filter-pills>
                                <button class="filter-pill active" type="button" data-filter="all">Toutes les catégories</button>
                                <?php foreach ($contextFilters as $filter): ?>
                                    <button class="filter-pill" type="button" data-filter="<?= htmlspecialchars($filter, ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($filter, ENT_QUOTES, 'UTF-8') ?></button>
                                <?php endforeach; ?>
                            </div>
                        </div>
                        <div class="col-12 col-lg-3">
                            <div class="shop-layout-switcher d-flex align-items-center gap-2 justify-content-lg-end">
                                <span class="text-muted small">Affichage</span>
                                <ul class="layout-switcher nav">
                                    <li class="switchergrid active" data-layout="grid"><i class="fa fa-th"></i></li>
                                    <li class="switcherlist" data-layout="layout-list"><i class="fa fa-th-list"></i></li>
                                </ul>
                            </div>
                        </div>
                        <div class="col-12 col-lg-2">
                            <div class="sort-by-wrapper">
                                <label for="sort" class="sr-only">Trier par</label>
                                <select name="sort" id="sort" class="nice-select">
                                    <option value="sbp">Popularité</option>
                                    <option value="sbn">Nouveautés</option>
                                    <option value="sbt">Tendance</option>
                                    <option value="sbr">Mieux notés</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="shop-page-product">
            <div class="container container-wide">
                <div class="product-wrapper product-layout layout-grid" id="trg">
                    <div class="row mtn-30" id="products">
                        <?php foreach ($products as $index => $product): ?>
                            <?php
                                $categoryName = $product->get('c');
                                $tags = [];
                                if ($index % 3 === 0) {
                                    $tags[] = 'promo';
                                }
                                if ($index % 4 === 0) {
                                    $tags[] = 'top';
                                }
                                if ($index % 5 === 0) {
                                    $tags[] = 'new';
                                }
                                $tagString = implode(',', $tags);
                            ?>
                            <div class="col-xl-2" data-category="<?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>" data-tags="<?= htmlspecialchars($tagString, ENT_QUOTES, 'UTF-8') ?>">
                                <div class="product-item">
                                    <div class="product-item__thumb">
                                        <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>">
                                            <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                            <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                        </a>
                                    </div>

                                    <div class="product-item__content">
                                        <div class="product-item__info">
                                            <h4 class="title" style="margin-top:15px;">
                                                <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>">
                                                    <?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>
                                                </a>
                                            </h4>
                                            <span class="price"><strong>Price:</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
                                        </div>

                                        <div class="product-item__action">
                                            <button class="btn-add-to-cart"><i class="ion-bag"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-ios-loop-strong"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-ios-heart-outline"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-eye"></i></button>
                                        </div>

                                        <div class="product-item__desc">
                                            <p>Pursue pleasure rationally encounter consequences that are extremely painful.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            </div>
        </div>

        <div class="shop-page-action-bar mt-30">
            <div class="container container-wide">
                <div class="action-bar-inner">
                    <div class="row align-items-center">
                        <div class="col-sm-6">
                            <nav class="pagination-wrap mb-10 mb-sm-0">
                                <ul class="pagination">
                                    <li class="active"><a href="#">1</a></li>
                                    <li><a href="#">2</a></li>
                                    <li><a href="#">3</a></li>
                                    <li><a href="#"><i class="ion-ios-arrow-thin-right"></i></a></li>
                                </ul>
                            </nav>
                        </div>

                        <div class="col-sm-6 text-center text-sm-right">
                            <p>Showing <?= count($products) ?> results</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer>
        <div class="container">
            <div class="footer clearfix mb-0 text-muted">
                <div class="float-start">
                    <p>2021 &copy; Mazer</p>
                </div>
                <div class="float-end">
                    <p>Crafted with <span class="text-danger"><i class="bi bi-heart"></i></span> by <a
                            href="https://saugi.me">Saugi</a></p>
                </div>
            </div>
        </div>
    </footer>

    <script src="<?= asset('assets/js/bootstrap.js') ?>"></script>
    <script src="<?= asset('assets/js/app.js') ?>"></script>
    <script src="<?= asset('assets/js/pages/horizontal-layout.js') ?>"></script>
    <script src="<?= asset('assets/extensions/apexcharts/apexcharts.min.js') ?>"></script>
    <script src="<?= asset('assets/js/pages/dashboard.js') ?>"></script>
    <script src="<?= asset('Customer/js.js') ?>"></script>
    <script>
        (function() {
            const params = new URLSearchParams(window.location.search);
            const initialCategory = params.get('id');
            const isPromo = params.get('promo') === '1';
            const products = document.querySelectorAll('#products > div');
            const filterPills = document.querySelectorAll('[data-filter]');
            const contextTabs = document.querySelectorAll('.context-tab');
            const savedSearchKey = 'inventaire_saved_searches';
            const savedSearchContainer = document.querySelector('.shop-context__saved-searches [data-saved-searches]');

            const updateColumnClass = (card, filter) => {
                card.classList.remove('col-xl-2', 'col-xl-3');
                if (filter && filter !== 'all') {
                    card.classList.add('col-xl-3');
                } else {
                    card.classList.add('col-xl-2');
                }
            };

            const applyFilter = (filter) => {
                products.forEach((card) => {
                    const category = card.getAttribute('data-category');
                    const tags = (card.getAttribute('data-tags') || '').split(',').filter(Boolean);
                    let visible = false;

                    if (!filter || filter === 'all') {
                        visible = true;
                    } else if (['promo', 'top', 'new'].includes(filter)) {
                        visible = tags.includes(filter);
                    } else {
                        visible = category === filter;
                    }

                    card.classList.toggle('not-active-prod', !visible);
                    updateColumnClass(card, visible && filter ? filter : null);
                });
            };

            const setActiveState = (elements, value, attribute) => {
                elements.forEach((element) => {
                    const elementValue = element.getAttribute(attribute);
                    element.classList.toggle('active', elementValue === value || (!value && elementValue === 'all'));
                });
            };

            const normalizeFilter = (value) => {
                if (!value) {
                    return 'all';
                }
                return value;
            };

            const renderSavedSearches = () => {
                if (!savedSearchContainer) {
                    return;
                }
                savedSearchContainer.innerHTML = '';
                const savedSearches = JSON.parse(localStorage.getItem(savedSearchKey) || '[]');
                if (!savedSearches.length) {
                    const empty = document.createElement('span');
                    empty.className = 'text-muted small';
                    empty.textContent = 'Aucune recherche enregistrée';
                    savedSearchContainer.appendChild(empty);
                    return;
                }

                savedSearches.forEach((term) => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'saved-search-chip';
                    button.textContent = term;
                    button.addEventListener('click', () => {
                        window.location.href = `${window.location.pathname}?q=${encodeURIComponent(term)}`;
                    });
                    savedSearchContainer.appendChild(button);
                });
            };

            const initialFilter = isPromo ? 'promo' : normalizeFilter(initialCategory);
            applyFilter(initialFilter);
            setActiveState(filterPills, initialFilter, 'data-filter');
            setActiveState(contextTabs, initialFilter, 'data-context-tab');

            filterPills.forEach((pill) => {
                pill.addEventListener('click', () => {
                    const value = pill.getAttribute('data-filter');
                    applyFilter(value);
                    setActiveState(filterPills, value, 'data-filter');
                    setActiveState(contextTabs, value, 'data-context-tab');
                });
            });

            contextTabs.forEach((tab) => {
                tab.addEventListener('click', () => {
                    const value = tab.getAttribute('data-context-tab');
                    applyFilter(value);
                    setActiveState(contextTabs, value, 'data-context-tab');
                    setActiveState(filterPills, value, 'data-filter');
                });
            });

            document.addEventListener('saved-searches:updated', renderSavedSearches);
            renderSavedSearches();
        })();
    </script>

    </div>
</div>
</div>

</body>

</html>
