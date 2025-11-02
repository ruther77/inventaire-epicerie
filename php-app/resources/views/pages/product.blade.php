@extends('layouts.app')

@section('title'){{ $product['name'] }}@endsection

@section('content')
<section class="max-w-4xl mx-auto px-6 py-12">
    <a href="/catalog" class="text-sm text-emerald-600">← {{ trans('messages.back_catalog') }}</a>
    <div class="mt-6 bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8">
            <div>
                <h1 class="text-3xl font-semibold text-slate-900 mb-2">{{ $product['name'] }}</h1>
                <p class="text-sm text-slate-500 uppercase tracking-wide">{{ ucfirst($product['category']) }}</p>
            </div>
            <span class="text-3xl font-bold text-emerald-600">€{{ number_format($product['price'], 2, ',', ' ') }}</span>
        </header>

        <p class="text-slate-700 leading-relaxed mb-8">{{ $product['description'] }}</p>

        <form method="post" action="/cart" class="flex items-center gap-3">
            @csrf
            <input type="hidden" name="product" value="{{ $product['slug'] }}">
            <label class="text-sm text-slate-600">{{ trans('messages.quantity') }}</label>
            <input type="number" name="quantity" value="1" min="1" class="w-20 border rounded-md px-3 py-2">
            <button type="submit" class="px-5 py-2 bg-emerald-600 text-white font-medium rounded-md hover:bg-emerald-700">{{ trans('messages.add_to_cart') }}</button>
        </form>
    </div>
</section>
@endsection
