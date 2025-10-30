<?php
require_once __DIR__ . '/../config/app.php';
require_once APP_ROOT . '/Metier/produit.php';

$title = 'Shop';
$products = Produit::afficher();

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
        <div class="shop-page-action-bar mb-30">
            <div class="container container-wide">
                <div class="action-bar-inner">
                    <div class="row align-items-center">
                        <div class="col-sm-10">
                            <div class="shop-layout-switcher mb-15 mb-sm-0">
                                <ul class="layout-switcher nav">
                                    <li class="switchergrid active" data-layout="grid"><i class="fa fa-th"></i></li>
                                    <li class="switcherlist" data-layout="layout-list"><i class="fa fa-th-list"></i></li>
                                </ul>
                            </div>
                        </div>

                        <div class="col-sm-2">
                            <div class="sort-by-wrapper">
                                <label for="sort" class="sr-only">Sort By</label>
                                <select name="sort" id="sort" class="nice-select">
                                    <option value="sbp">Sort By Popularity</option>
                                    <option value="sbn">Sort By Newest</option>
                                    <option value="sbt">Sort By Trending</option>
                                    <option value="sbr">Sort By Rating</option>
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
                        <?php foreach ($products as $product): ?>
                            <?php $categoryName = $product->get('c'); ?>
                            <div class="col-xl-2" data-category="<?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>">
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
        if (selectedCategory) {
            document.querySelectorAll('#products > div').forEach((card) => {
                const category = card.getAttribute('data-category');
                if (category !== selectedCategory) {
                    card.classList.add('not-active-prod');
                } else {
                    card.classList.remove('not-active-prod');
                    card.classList.add('col-xl-3');
                }
            });
        }
    </script>

    </div>
</div>
</div>

</body>

</html>
