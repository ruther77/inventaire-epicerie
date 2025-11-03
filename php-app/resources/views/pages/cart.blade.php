@extends('layouts.app')

@section('title'){{ trans('messages.cart') }}@endsection

@section('content')
<section class="max-w-4xl mx-auto px-6 py-12">
    <h1 class="text-3xl font-semibold text-slate-900 mb-6">{{ trans('messages.cart') }}</h1>

    @if (empty($items))
        <p class="text-slate-500">{{ trans('messages.empty_cart') }}</p>
    @else
        <div class="space-y-4">
            @foreach ($items as $item)
                <div class="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-4">
                    <div>
                        <h2 class="font-semibold text-slate-900">{{ $item['product']['name'] }}</h2>
                        <p class="text-sm text-slate-500">{{ $item['quantity'] }} × €{{ number_format($item['product']['price'], 2, ',', ' ') }}</p>
                    </div>
                    <span class="text-lg font-semibold text-emerald-600">€{{ number_format($item['product']['price'] * $item['quantity'], 2, ',', ' ') }}</span>
                </div>
            @endforeach
        </div>

        <div class="mt-6 flex items-center justify-between">
            <span class="text-xl font-semibold text-slate-900">{{ trans('messages.total') }}</span>
            <span class="text-2xl font-bold text-emerald-600">€{{ number_format($total, 2, ',', ' ') }}</span>
        </div>

        <form method="post" action="/cart/clear" class="mt-6">
            @csrf
            <button type="submit" class="px-5 py-2 border border-slate-300 rounded-md text-sm text-slate-600 hover:bg-slate-50">{{ trans('messages.clear_cart') }}</button>
        </form>
    @endif
</section>
@endsection
