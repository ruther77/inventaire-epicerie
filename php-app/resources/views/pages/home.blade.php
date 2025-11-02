@extends('layouts.app')

@section('title'){{ trans('messages.home_title') }}@endsection

@section('content')
<section class="bg-gradient-to-r from-emerald-500 to-emerald-600 text-white py-16">
    <div class="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center gap-10">
        <div class="flex-1">
            <h1 class="text-4xl font-semibold mb-4">{{ trans('messages.hero_title') }}</h1>
            <p class="text-lg text-emerald-100 mb-6">{{ trans('messages.hero_subtitle') }}</p>
            <div class="flex flex-wrap gap-3">
                <a href="/catalog" class="px-5 py-2.5 bg-white text-emerald-700 font-medium rounded-md">{{ trans('messages.cta_shop') }}</a>
                <a href="/contact" class="px-5 py-2.5 border border-white text-white font-medium rounded-md">{{ trans('messages.cta_contact') }}</a>
            </div>
        </div>
        <div class="flex-1 bg-white/10 rounded-lg p-6">
            <h2 class="text-sm uppercase tracking-wide text-emerald-100 mb-2">{{ trans('messages.top_categories') }}</h2>
            <ul class="space-y-2 text-emerald-50">
                @foreach ($categories as $category)
                    <li class="flex items-center justify-between">
                        <span>{{ ucfirst($category) }}</span>
                        <span class="text-xs uppercase">{{ trans('messages.curated') }}</span>
                    </li>
                @endforeach
            </ul>
        </div>
    </div>
</section>

<section class="max-w-6xl mx-auto px-6 py-16">
    <header class="flex items-center justify-between mb-8">
        <div>
            <h2 class="text-2xl font-semibold text-slate-900">{{ trans('messages.featured_products') }}</h2>
            <p class="text-sm text-slate-500">{{ trans('messages.featured_subtitle') }}</p>
        </div>
        <a href="/catalog" class="text-sm text-emerald-600 font-medium">{{ trans('messages.view_catalog') }}</a>
    </header>
    @component('components.product-grid', ['products' => $featured])
    @endcomponent
</section>
@endsection
