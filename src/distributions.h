// stdafx.h : include file for standard system include files,
// Use Boost::Python as interface between Python and Boost::math::distributions

#pragma once
#include <boost/python.hpp>
#include <boost/math/distributions/non_central_chi_squared.hpp>


// Interface
double qchisq(const double df, const double alpha);
double pchisq(const double df, const double lambda, const double x);
