import numpy as np
import astropy.table 
from scipy.interpolate import interp1d

import matplotlib.pyplot as plt
from ipdb import set_trace as stop

import atlas 

def spectrum(wave, spec, spec_avg=None, cgs=True,
        si=False, perHz=True, calib_wave=False, wave_ref=None,
        wave_idx=None, verbose=False):
    """
    Calibrate spectrum intensity in SI or cgs units

    Arguments:
        wave: 1D array with wavelengths. Must be of same size as `spec`.
        spec: 1D array with intensity profile in data counts to calibrate. If
            keyword argument `spec_avg` is None, then `spec` will be used for
            the intensity (and wavelength) calibration.

    Keyword arguments:
        spec_avg: averaged intensity profile to use for calibration
            (default None -> use `spec` to calibrate on)
        cgs: output calibration in cgs units (default True)
        si: output calibration in SI units (default False)
        perHz: output calibration per frequency unit (default True)
        calib_wave: perform wavelength calibration prior to intensity
            calibration (default False)
        wave_ref: reference wavelength to clip around in determining line centre
            wavelength for the wavelength calibration (default None -> determine
            from profile)
        wave_idx: wavelength indices to determine the average calibration offset
            over (default None -> use all wavelengths)

    Returns:
        wave: calibrated wavelength array
        spec: calibrated intensity profile array
        factor: offset factor converting data counts to absolute intensity
        spec_fts: atlas profile at wavelengths given by `wave`
        unit: intensity units

    Example:
        wave_cal, spec_cal, factor, spec_fts, units = calib.spectrum(ispec,
            wave, cgs=True, calib_wave=True, wave_idx=[0,1,-2,-1]

    Author:
        Gregal Vissers (ISP/SU 2019)
    """

    wave = np.copy(wave)
    spec = np.copy(spec)
    if spec_avg is not None:
        profile = spec_avg
    else:
        profile = spec
    
    if wave_idx is None:
        wave_idx = np.arange(wave.size)

    # Get atlas profile for range +/- 0.3
    fts = atlas.atlas()
    wave_fts, spec_fts, cont_fts = fts.get(wave[0]-0.3, wave[-1]+0.3, cgs=cgs, si=si, perHz=perHz)

    # Calibrate wavelength
    if calib_wave is True:
        wave = wavelength(wave, profile, wave_fts, spec_fts, wave_ref=wave_ref,
                verbose=verbose)

    spec_fts_sel = []
    for ww in range(wave.size):
        widx = np.argmin(np.abs(wave_fts - wave[ww]))
        spec_fts_sel.append(spec_fts[widx])
    offset_factors = 1. / (profile / spec_fts_sel)
    factor = offset_factors[wave_idx].mean()

    spec *= factor

    if verbose is True:
        plot_scale_factor = 1.e-5
        fig, ax = plt.subplots()
        ax.plot(wave, spec/plot_scale_factor, '.')
        ax.plot(wave[wave_idx], spec[wave_idx]/plot_scale_factor, '+')
        ax.plot(wave_fts, spec_fts/plot_scale_factor)
        ax.set_ylabel('intensity ['+r'$\times10^{-5}$'+' {0}]'.format(fts.sunit.to_string()))
        ax.set_xlabel('wavelength [{0}]'.format(fts.wunit.to_string()))
        ax.legend(('observed profile', 'selected points', 'atlas profile'))
        ax.set_title('ISPy: calib.spectrum() results')
        plt.show()
        print("spectrum: intensity calibration offset factor: {0}".format(factor))

    return wave, spec, factor, spec_fts_sel, fts.sunit



def wavelength(wave, spec, wave_fts, spec_fts, wave_ref=None, dwave_ref=0.2,
        verbose=False):
    """
    Calibrate spectrum in SI or cgs units

    Arguments:
        wave: 1D array with wavelengths. Must be of same size as `spec`.
        spec: 1D array with intensity profile.
        wave_fts: 1D array with atlas profile wavelengths. Must be of same size
            as `spec_fts`.
        spec_fts: 1D array with atlas profile

    Keyword arguments:
        wave_ref: reference wavelength to clip around in determining line centre
            wavelength for the wavelength calibration (default None -> determine
            from profile)
        dwave_ref: clipping range around reference wavelength to determine line
            centre minimum from (default 0.2)

    Returns:
        wave: calibrated wavelength array

    Example:
        wave_cal = wavelength(spec, wave, spec_fts, wave_fts)j

    Author:
        Gregal Vissers (ISP/SU 2019)
    """
    inam = 'wavelength'
  
    wave_spacing = np.diff(wave).mean()

    if wave_ref is None:
        wave_ref = wave[wave.size//2]

    wave_fine = np.arange((wave.size-1)*100.+1)*wave_spacing/100. + wave[0]
    spline = interp1d(wave, spec, kind='cubic')
    spec_fine = spline(wave_fine)
    widx = np.where((wave_fine >= wave_ref-dwave_ref) & \
            (wave_fine <= wave_ref+dwave_ref))[0]
    wave_min = wave_fine[widx[np.argmin(spec_fine[widx])]]

    widx = np.where((wave_fts >= wave_ref-dwave_ref) & \
            (wave_fts <= wave_ref+dwave_ref))[0]
    wave_fts_min = wave_fts[widx[np.argmin(spec_fts[widx])]]

    wave_offset = wave_fts_min - wave_min
    if verbose is True:
        print("{0}: input profile minimum at: {1}".format(inam, wave_min))
        print("{0}: atlas profile minimum at: {1}".format(inam, wave_fts_min))
        print("{0}: calibrated offset: {1} (added to input wavelengths)".format(inam, wave_offset))

    wave += wave_offset

    return wave
    
