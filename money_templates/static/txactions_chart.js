var charts = {
        expenses : {},
        income   : {}
    },
    spans = {};

spans.day  = 24*60*60*1000;
spans.week = 7 * spans.day;

$(function() {
    $('#load-charts').on('click', function() {
        $('#load-charts-container').hide();
        $('#charts-container').show();
        loadCharts();
    });
});

function loadCharts() {
    var data = $.extend({
        accounts : currentAccountsKey
    }, queryParams);

    $.ajax({
        url     : apiFunctionUrls['get_transactions'],
        type    : 'GET',
        data    : data,
        cache   : false,
        success : function(d) {
            drawSplitsChart(charts.expenses, {
                splits          : d.splits,
                selector        : '#expenses-chart',
                reorderSelector : '#expenses-reorder',
                filter          : function(amount) { return amount < 0; }
            });
            drawSplitsChart(charts.income, {
                splits          : d.splits,
                selector        : '#income-chart',
                reorderSelector : '#income-reorder',
                filter          : function(amount) { return amount > 0; }
            });
        },
        error : function(xhr, status, e) {
            $('#expenses-chart, #income-chart').html(
                'Error loading: '
                + (e.message || xhr.status)
                + ' (' + status + ')');
        },
        complete : function(xhr, status) {
            // nothing to do here I guess
        }
    });

    $('#chart-controls').on('click', '.chart-period', function() {
        var top = $(window).scrollTop();
        drawSplitsChart(charts.expenses, {
            period : $(this).data('period')
        });
        drawSplitsChart(charts.income, {
            period : $(this).data('period')
        });
        $(window).scrollTop(top);
        return false;
    });
}

function getPeriodForDate(chart, d) {
    var date = moment(d);

    switch (chart.period) {
        case 'weekly':
            return Math.floor((date - chart.firstPeriod) / spans.week);
        case 'biweekly':
            return Math.floor((date - chart.firstPeriod) / spans.week / 2);
        case 'monthly':
            return date.year() * 12 + date.month() - chart.firstPeriodYearMonth;
    }
}

function getDateForPeriod(chart, p) {
    switch (chart.period) {
        case 'weekly':
            return moment(chart.firstPeriod + p * spans.week);
        case 'biweekly':
            return moment(chart.firstPeriod + p * 2 * spans.week);
        case 'monthly':
            var yearMonth = chart.firstPeriodYearMonth + p;
            return moment({
                year  : Math.floor((yearMonth - 1) / 12),
                month : (yearMonth - 1) % 12 + 1 - 1, // js starts from 0
                day   : 1
            }).add(1, 'month').endOf('month'); // off by one somewhere...
    }
}

function drawSplitsChart(chart, config) {
    $.extend(chart, config || {});

    if (chart.c3) {
        chart.c3.destroy();
        chart.c3 = null;
    }

    chart.minDate = Infinity;
    chart.maxDate = -Infinity;
    chart.splits.forEach(function(s) {
        chart.minDate = Math.min(chart.minDate, s.post_date);
        chart.maxDate = Math.max(chart.maxDate, s.post_date);
    });

    if (!chart.period) {
        var begin = moment(chart.minDate);
        if (chart.maxDate - chart.minDate <= 8 * spans.week) {
            chart.period = 'weekly';
            begin = begin.startOf('week');
        } else if (chart.maxDate - chart.minDate <= 16 * spans.week) {
            chart.period = 'biweekly';
            begin = begin.startOf('week');
            if (begin.isoWeek() % 2 == 0) {
                begin = begin.isoWeek(begin.isoWeek() - 1);
            }
        } else {
            chart.period = 'monthly';
            begin = begin.startOf('month');
            chart.firstPeriodYearMonth = begin.year() * 12 + begin.month();
        }
        chart.firstPeriod = +begin;
    }

    d3.selectAll('#chart-controls .chart-period')
        .classed('active', function() {
            return $(this).data('period') == chart.period;
        });

    if (!chart.filter) {
        chart.filter = function(amount) { return amount > 0 };
    }

    chart.maxPeriodNum = getPeriodForDate(chart, chart.maxDate);

    chart.accounts     = {};
    chart.data         = [];
    chart.xValues      = ['x'];

    var accountIndex = 0;

    function addAccount(account) {
        if (!chart.accounts[account.guid]) {
            account.order = accountIndex++;
            chart.accounts[account.guid] = account;
            chart.data.push([account.friendly_name].concat(
                Array.apply(null, new Array(chart.maxPeriodNum + 1))
                .map(function() {
                    return 0;
                })
            ));
        }
    }

    for (var i = 0; i <= chart.maxPeriodNum; i++) {
        chart.xValues.push(getDateForPeriod(chart, i).format('YYYY-MM-DD'));
    }

    (chart.order || []).forEach(addAccount);

    chart.splits.forEach(function(s) {
        s.amount = Number(s.amount);
        if (chart.filter(s.amount)) {
            addAccount(s.opposing_account);
            var account = chart.accounts[s.opposing_account.guid];
            if (account) {
                var series = chart.data[account.order],
                    period = getPeriodForDate(chart, s.post_date);
                series[period + 1] = (series[period + 1] || 0) + Math.abs(s.amount);
            }
        }
    });

    $(chart.reorderSelector).html(chart.data.map(function(series) {
        return series[0]; // account friendly name
    }).join(', '));

    $('#chart-controls').show();

    chart.c3 = c3.generate({
        bindto : chart.selector,
        data   : {
            x       : 'x',
            columns : [chart.xValues].concat(chart.data),
            type    : 'area',
            groups  : [chart.data.map(function(series) { return series[0]; })],
            order   : null
        },
        axis : {
            x : {
                type : 'timeseries',
                tick : {
                    format : '%Y-%m-%d'
                }
            }
        }
    });
}
