<!DOCTYPE html>
<html lang="fr" class="h-full bg-slate-50">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ trans('messages.site_title') }}@php $pageTitle = trim($__env->yieldSection('title')); echo $pageTitle !== '' ? ' — ' . e($pageTitle) : ''; @endphp</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tailwindcss@3.4.13/dist/tailwind.min.css">
</head>
<body class="min-h-full flex flex-col">
@php $currentLocale = app()->get(Framework\I18n\Translator::class)->locale(); @endphp
<header class="bg-white shadow-sm">
    <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="/" class="text-2xl font-semibold text-emerald-700">Inventaire Épicerie</a>
        <nav class="flex items-center gap-4 text-sm text-slate-600">
            <a href="/catalog" class="hover:text-emerald-600">{{ trans('messages.catalog') }}</a>
            <a href="/cart" class="hover:text-emerald-600">{{ trans('messages.cart') }}</a>
            <a href="/contact" class="hover:text-emerald-600">{{ trans('messages.contact') }}</a>
        </nav>
        <form class="flex items-center gap-2">
            <select name="locale" data-controller="locale" data-action="change->locale#switch" class="border rounded-md px-2 py-1">
                <option value="fr" @if($currentLocale === 'fr') selected @endif>FR</option>
                <option value="en" @if($currentLocale === 'en') selected @endif>EN</option>
            </select>
        </form>
    </div>
</header>

<main class="flex-1">
    @php $statusMessage = session()->message('status'); @endphp
    @if ($statusMessage)
        <div class="max-w-4xl mx-auto px-6 pt-6">
            <div class="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-800 text-sm">
                {{ $statusMessage }}
            </div>
        </div>
    @endif
    @yield('content')
</main>

<footer class="bg-slate-900 text-slate-100 py-8 mt-12">
    <div class="max-w-6xl mx-auto px-6 flex flex-col gap-2 text-sm">
        <span>&copy; {{ date('Y') }} Inventaire Épicerie</span>
        <span>{{ trans('messages.footer_tagline') }}</span>
    </div>
</footer>

<script type="module">
    import { Application, Controller } from 'https://cdn.skypack.dev/@hotwired/stimulus';

    const app = Application.start();

    app.register('product-filter', class extends Controller {
        static targets = ['search', 'category', 'grid', 'count'];

        connect() {
            this.timeout = null;
            this.element.querySelector('form').addEventListener('submit', (event) => {
                event.preventDefault();
            });
        }

        change() {
            clearTimeout(this.timeout);
            this.timeout = setTimeout(() => this.fetch(), 150);
        }

        fetch() {
            const formData = new FormData(this.element.querySelector('form'));

            fetch('/livewire/products/filter', {
                method: 'POST',
                body: formData,
            })
                .then((response) => response.json())
                .then((data) => {
                    this.gridTarget.innerHTML = data.html;
                    this.countTarget.textContent = data.count;
                });
        }
    });

    app.register('locale', class extends Controller {
        switch(event) {
            const value = event.target.value;
            window.location.href = `/locale/${value}`;
        }
    });
</script>
</body>
</html>
