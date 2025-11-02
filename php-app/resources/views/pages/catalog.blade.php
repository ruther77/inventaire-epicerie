@extends('layouts.app')

@section('title'){{ trans('messages.catalog') }}@endsection

@section('content')
<section class="bg-white border-b border-slate-200">
    <div class="max-w-6xl mx-auto px-6 py-12" data-controller="product-filter">
        <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8">
            <div>
                <h1 class="text-3xl font-semibold text-slate-900">{{ trans('messages.catalog_intro') }}</h1>
                <p class="text-sm text-slate-500">{{ trans('messages.catalog_subtitle') }}</p>
            </div>
            <div class="text-sm text-slate-500">
                <span>{{ trans('messages.products_count') }}</span>
                <span class="ml-1 font-medium text-slate-900" data-product-filter-target="count">{{ count($products) }}</span>
            </div>
        </header>

        <form class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10" method="get" data-action="input->product-filter#change change->product-filter#change">
            <input type="hidden" name="_token" value="{{ app()->session()->token() }}">
            <div class="md:col-span-2">
                <label class="block text-xs uppercase text-slate-500 mb-1">{{ trans('messages.search') }}</label>
                <input type="text" name="search" value="{{ $searchTerm }}" class="w-full border rounded-md px-3 py-2" data-product-filter-target="search">
            </div>
            <div class="md:col-span-1">
                <label class="block text-xs uppercase text-slate-500 mb-1">{{ trans('messages.filter_category') }}</label>
                <select name="category" class="w-full border rounded-md px-3 py-2" data-product-filter-target="category">
                    <option value="">{{ trans('messages.all_categories') }}</option>
                    @foreach ($categories as $category)
                        <option value="{{ $category }}" @if ($selectedCategory === $category) selected @endif>{{ ucfirst($category) }}</option>
                    @endforeach
                </select>
            </div>
            <div class="md:col-span-1 flex items-end">
                <a href="/catalog" class="inline-flex items-center px-4 py-2 border border-slate-200 rounded-md text-sm text-slate-600 hover:bg-slate-50">{{ trans('messages.reset_filters') }}</a>
            </div>
        </form>

        <div data-product-filter-target="grid">
            @component('components.product-grid', ['products' => $products])
            @endcomponent
        </div>
    </div>
</section>
@endsection
