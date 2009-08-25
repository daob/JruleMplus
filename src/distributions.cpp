#include "distributions.h"


BOOST_PYTHON_MODULE(distributions)
{
    using namespace boost::python;
    def("qchisq", qchisq);
    def("pchisq", pchisq);
}


double 
qchisq(const double df, const double alpha) 
{
    double cs = quantile(complement(boost::math::chi_squared(df), alpha));
    return(cs);
}

double
pchisq(const double df, const double lambda, const double x)
{
    double pr = cdf(complement(boost::math::non_central_chi_squared(df, lambda),  x));
    return(pr);
}
