
#ifndef MIRAO52E_INCLUDED
#define MIRAO52E_INCLUDED


#ifdef __cplusplus
extern "C" {
#endif

#include <time.h>





//////////////////////////////////////
// CALLING CONVENTIONS MACROS
//////////////////////////////////////

#define MIRAOEXPORT __declspec(dllexport)
#define MIRAOIMPORT __declspec(dllimport)
#define MIRAOCALL   __stdcall





//////////////////////////////////////
// MIRAO CONSTANTS DEFINITION
//////////////////////////////////////

#define MRO_TRUE	1		/**< TRUE MroBoolean value. */
#define MRO_FALSE	0		/**< FALSE MroBoolean value. */


/**
 * Number of values of a mirao 52-e command.
 */
#define	MRO_NB_COMMAND_VALUES		52





//////////////////////////////////////
// MIRAO ERRORS DEFINITION
//////////////////////////////////////

/**
 * No error detected. 
 */
const int MRO_OK = 0;

/**
 * Unknown error.
 * Indicates an error of unknown provenance 
 * has been detected.
 */
const int MRO_UNKNOWN_ERROR = 1;

/**
 * mirao 52-e device is not opened.
 * Indicates a successful call to mro_open must be done 
 * before calling other functions.
 */
const int MRO_DEVICE_NOT_OPENED_ERROR = 2;

/**
 * mirao 52-e device has been identified as defective.
 * The hardware configuration of the mirao 52-e device seems to be defective.
 */
const int MRO_DEFECTIVE_DEVICE_ERROR = 3;

/**
 * mirao 52-e is already opened.
 * You try to call twice the mro_open function without having 
 * closed mirao 52-e device before.
 */
const int MRO_DEVICE_ALREADY_OPENED_ERROR = 4;

/**
 * A communication error has been detected.
 * mirao 52-e device has detected a communication anomaly.
 */
const int MRO_DEVICE_IO_ERROR = 5;

/**
 * mirao 52-e is locked.
 * A temperature overheat or an excess of current has lead mirao 52-e
 * to a protection state.
 * A zero command has been applied waiting for device safety and 
 * you are not allowed to apply commands till it.<br>
 * <i>This error is raised only if the monitoring is enabled</i>.
 */
const int MRO_DEVICE_LOCKED_ERROR = 6;

/**
 * mirao 52-e seems to be disconnected.
 * The connection with mirao 52-e has been lost. Check cables.<br>
 * <i>This error is raised only if the monitoring is enabled</i>.
 */
const int MRO_DEVICE_DISCONNECTED_ERROR = 7;

/**
 *	
 * This error indicates an internal driver malfunction.
 */
const int MRO_DEVICE_DRIVER_ERROR = 8;

/**
 * The file already exists.
 * The file to write already exists and it's not allowed 
 * to overwrite it.
 */
const int MRO_FILE_EXISTS_ERROR = 9;

/**
 * Bad file format.
 * The considered file is corrupted or has not a valid file format.
 */
const int MRO_FILE_FORMAT_ERROR = 10;

/**
 * An error has been detected while reading/writing a file.
 * This error can indicate a problem with the hard drive.
 */
const int MRO_FILE_IO_ERROR = 11;

/**
 * Invalid command.
 * There are two possibilities: <br>
 * - A least one of the values of the command is out of specification (value > 1.0 or value < -1.0).
 * - The sum of the absolute values of the command's values is greater than 25.0.
 */
const int MRO_INVALID_COMMAND_ERROR = 12;

/**
 * Null pointer error.
 * A null pointer has been identified as a parameter which cannot be null.
 */
const int MRO_NULL_POINTER_ERROR = 13;

/**
 * A parameter is out of accepted bounds.
 * This happens when an index parameter is out of its possible values.
 */
const int MRO_OUT_OF_BOUNDS_ERROR = 14;

/**
 * Operation already in progress.
 * The requested operation cannot be performed due to a synchronization lock. 
 */
const int MRO_OPERATION_ONGOING_ERROR = 15;

/**
 * Operating system error.
 * An error has been detected while calling the operating system.
 */
const int MRO_SYSTEM_ERROR = 16;

/**
 * The requested data is unavailable.
 * This can be due to the call of an unavailable functionality or a 
 * functionality that needs monitoring to be enabled.
 */
const int MRO_UNAVAILABLE_DATA_ERROR = 17;

/**
 * Undefined value.
 * The requested value is not available. Ex: request of an undefined stock command value.
 */
const int MRO_UNDEFINED_VALUE_ERROR = 18;

/**
 * A parameter has an out of specifications value.
 * The value, which is not an index, is out of allowed values.
 */
const int MRO_OUT_OF_SPECIFICATIONS_ERROR = 19;

/**
 * The file format version is not supported.
 * The version of the MRO file format is not handled by this mirao 52-e API.
 */
const int MRO_FILE_FORMAT_VERSION_ERROR = 20;

/**
 * Invalid handle.
 * This error implies either an operating system error or an internal driver error.
 */
const int MRO_USB_INVALID_HANDLE = 21;

/**
 * mirao 52-e cannot be found.
 * mirao 52-e device cannot be found among the USB ports.
 * There may be several possibilities:
 * - The device is not connected to the computer or the connection is defective,
 * - The USB port is not correctly installed in the operating system,
 * - The mirao 52-e device is not turned ON,
 * - The mirao 52-e device is already opened by another process,
 * - The mirao 52-e device is defective.
 */
const int MRO_USB_DEVICE_NOT_FOUND = 22;

/**
 * Internal driver not opened.
 * This error implies an operating system error.
 */
const int MRO_USB_DEVICE_NOT_OPENED = 23;

/**
 * Internal driver IO error.
 * The internal driver encountered a problem for reading from or writing to the
 * hardware device.
 */
const int MRO_USB_IO_ERROR = 24;

/**
 * Insufficient resources.
 * There are insufficient system resources to perform the requested operation.
 */
const int MRO_USB_INSUFFICIENT_RESOURCES = 25;

/**
 * Invalid baud rate.
 * The configuration of the connection speed is not supported.
 */
const int MRO_USB_INVALID_BAUD_RATE = 26;

/**
 * Operation not supported.
 * A functionnality is not supported by the internal driver. Implies an operating 
 * system error perhaps due to a bad USB driver version.
 */
const int MRO_USB_NOT_SUPPORTED = 27;

/**
 * Permission denied.
 * A file cannot be accessed due to a permission denied error.
 */
const int MRO_FILE_IO_EACCES = 28;

/**
 * No more processes.
 * An attempt to create a new process failed.
 */
const int MRO_FILE_IO_EAGAIN = 29;

/**
 * Bad file number.
 * An invalid internal file descriptor has been used.
 * This is an operating system error.
 */
const int MRO_FILE_IO_EBADF = 30;

/**
 * Invalid argument.
 * An internal invalid argument has been used with a file IO function.
 * This is an operating system error.
 */
const int MRO_FILE_IO_EINVAL = 31;

/**
 * Too many opened files.
 * The maximum number of open files allowed by the operating system has been reached.
 */
const int MRO_FILE_IO_EMFILE = 32;

/**
 * No such file or directory.
 * The considered file or directory does not exists.
 */
const int MRO_FILE_IO_ENOENT = 33;

/**
 * Not enough memory.
 * The operation requested cannot be performed because the process is out of memory.
 */
const int MRO_FILE_IO_ENOMEM = 34;

/**
 * No space left on device.
 * A file cannot be written because the hard drive lacks of space.
 */
const int MRO_FILE_IO_ENOSPC = 35;





//////////////////////////////////////
// MIRAO TYPES DEFINITION
//////////////////////////////////////

/**
 * mirao 52-e command.
 * Array of 52 double values representing the geometry of the mirror.
 * @see	MRO_NB_COMMAND_VALUES
 */
typedef double *MroCommand;

/**
 * mirao 52-e date.
 * This type is an ISO C programming language time format.
 */
typedef time_t  MroDate;

/**
 * mirao 52-e boolean.
 * The allowed type values are MRO_TRUE and MRO_FALSE.
 * @see	MRO_TRUE
 * @see	MRO_FALSE
 */
typedef char    MroBoolean;

/**
 * mirao 52-e temperature.
 * A temperature expressed in degrees Celsius (°C).
 */
typedef double  MroTemperature;

/**
 * mirao 52-e intensity.
 * An electric current intensity in Amperes (A).
 */
typedef double  MroIntensity;

/**
 * mirao 52-e event information.
 * Contains information about the mirao 52-e device. <br>
 * This structure is used as parameter of the callback function registered with
 * mro_registerCallback.
 * @see	mro_registerCallback
 */
typedef struct MroInfo {

	// Event identification
	static const int MIRAO_LOCKED_EVENT = 1;				/**< The mirao 52-e device has been locked. */
	static const int MIRAO_UNLOCKED_EVENT = 2;				/**< The mirao 52-e device has been unlocked. */
	static const int MIRAO_DATA_TRANSMISSION_ERROR = 3;		/**< A data transmission error occured. */
	static const int MIRAO_CONNECTION_LOST_EVENT = 4;		/**< The connection to the device has been lost. */
	static const int MIRAO_CONNECTION_RECOVERED_EVENT = 5;	/**< The connection to the device has been recovered. */
	static const int MIRAO_MONITORING_STARTED = 6;			/**< The monitoring has been started. */
	static const int MIRAO_MONITORING_STOPPED = 7;			/**< The monitoring has been stopped. */

	// Structure data
	double mirrorTemperature;			/**< Mirror temperature in degrees Celsius. */
	double powerSupplyTemperature;		/**< Power supply temperature in degrees Celsius. */
	double positiveCoilsIntensity;		/**< Current in the positive power supply in Amperes. */
	double negativeCoilsIntensity;		/**< Current in the negrative power supply in Amperes. */
	MroBoolean isMiraoLocked;			/**< MRO_TRUE if the mirao 52-e is locked, else MRO_FALSE. */
	MroBoolean isMiraoConnected;		/**< MRO_TRUE if the mirao 52-e is connected, MRO_FALSE if a connection problem is detecetd. */
	MroBoolean isMonitoringEnabled;		/**< MRO_TRUE if the monitoring is enabled, else MRO_FALSE. */
	int eventType;						/**< Event identifier (see "Event identification" above). */

} MiraoInfo;



///////////////////////////////////////////////////////////////////////////////
//	MIRAO FUNCTIONS
///////////////////////////////////////////////////////////////////////////////


/**
 * Indicates the mirao 52-e DLL version.
 * Returns a null terminated character string containing the version of the 
 * mirao 52-e DLL. The format of the version is "xxx.xxx.yyyymmdd".
 *
 * @param	version	Pointer to a character string to put the version.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the version has been copied into <i>version</i>, 
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_NULL_POINTER_ERROR		The parameter <i>version</i> is null.
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getVersion(
	char* version,
	int* status
	);


/**
 * Opens mirao 52-e.
 * Starts the communication with the mirao 52-e device and initializes it. <br>
 * At starting, the mirao 52-e device has a geometry of a command composed of a set
 * of null values. <br>
 * The monitoring is disable at starting. <br>
 * This function must be called before all the others (except mro_getVersion, 
 * mro_readCommandFile and mro_writeCommandFile).
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if mirao 52-e device is successfully opened, 
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_ALREADY_OPENED_ERROR		The mirao 52-e device is already opened.
 * @throw	MRO_DEFECTIVE_DEVICE_ERROR			The hardware configuration of the mirao 52-e device seems to be invalid.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVCIE_DRIVER_ERROR				An error occured while using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is no more valid.
 * @throw	MRO_USB_DEVICE_NOT_FOUND			The mirao device cannot be found.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The USB port is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error with the USB port occured.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		Insufficient system resources to perform the operation on the USB port.
 * @throw	MRO_USB_INVALID_BAUD_RATE			The USB port baud rate configuration is invalid.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 *
 * @see	mro_close
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_open(
	int* status
	);


/**
 * Closes mirao 52-e.
 * Resets the geometry with a command composed of null values, disables the
 * monitoring if it is enabled and closes the communication with the hardware.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the mirao 52-e device is successfully closed,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured while using the USB port.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The device is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error on the USB port occured.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		Insufficient system resources to perform the operation on the USB port.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 *
 * @see	mro_open
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_close(
	int* status
	);


/*-----------------------------------------------------------------------------
 * Command applying functions
 */


/**
 * Applies a standard command to the mirror.
 * The function modifies the geometry of the mirror
 * according to the set of values contained in <i>command</i>. <br>
 * If <i>trig</i> is MRO_TRUE, a hardware trig follow the application. <br>
 * With this function, the geometry of the mirror is changed as quickly as
 * possible.
 *
 * @param	command		Command to apply to the mirror.
 *
 * @param	trig		If MRO_TRUE, a hardware trig will follow the command
 *						application.
 *
 * @param	status		Pointer to an integer containing the error code if an error
 *						occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the command has been successfully sent to the mirror,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_INVALID_COMMAND_ERROR			The set of values contained in <i>command</i> is invalid.
 * @throw	MRO_NULL_POINTER_ERROR				The parameter <i>command</i> is NULL.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVICE_LOCKED_ERROR				The mirao 52-e device is locked.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured while using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The device is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error on the USB port occured.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		Insufficient system resources to perform the operation on the USB port.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 * @throw	MRO_DEVICE_DISCONNECTED				A communication problem with the mirao 52-e device has been detected.
 *
 * @see MroCommand
 * @see mro_applySmoothCommand
 * @see mro_applyStockCommand
 * @see mro_applySmoothStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_applyCommand( 
	MroCommand command, 
	MroBoolean trig,
	int* status
	);


/**
 * Not documented.
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_applyIoCommand( 
	MroCommand command,
	MroBoolean trig,
	int* status
	);


/**
 * Applies a smooth command to the mirror.
 * This function modifies the geometry of the mirror according to the set of
 * values contained in <i>command</i>. <br>
 * With this function, the geometry of the mirror is modified without 
 * vibrations but taking a little more time than with the <i>mro_applyCommand</i>
 * function. <br>
 * If <i>trig</i> is MRO_TRUE, a hardware trig follow the application. <br>
 *
 * @param	command		Command to apply to the mirror.
 * @param	trig		If MRO_TRUE, a hardware trig follow the command
 *						application.
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the command has been successfully sent to the mirror,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_INVALID_COMMAND_ERROR			The set of values contained in <i>command</i> is invalid.
 * @throw	MRO_NULL_POINTER_ERROR				The parameter <i>command</i> is NULL.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVICE_LOCKED_ERROR				The mirao 52-e device is in protection mode.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured while using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The USB port is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error on the USB port occured.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		Insufficient system resources to perform the operation on the USB port.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 * @throw	MRO_DEVICE_DISCONNECTED				A communication problem with the mirao 52-e device has been detected.
 *
 * @see	MroCommand
 * @see mro_applyCommand
 * @see mro_applyStockCommand
 * @see mro_applySmoothStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_applySmoothCommand( 
	MroCommand command, 
	MroBoolean trig,
	int* status
	);


/**
 * Indicates the last command applied to the mirror.
 * The last command applied to the mirror is copied into <i>command</i>. <br>
 * The last applied command is the last command applied to the mirror by the
 * user, or by the DLL in the functions mro_open and after a connection 
 * recovering.
 *
 * @param	command		Array where the last applied command is copied.
 *
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the last applied command has been copied in <i>command</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>command</i> is NULL.
 *
 * @see	MroCommand
 * @see	mro_getLastAppliedCommandDate
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getLastAppliedCommand( 
	MroCommand command,
	int* status
	);


/**
 * Indicates the date of the last command application.
 * Returns the date corresponding to the application of the command available 
 * through the function mro_getLastAppliedCommand. <br>
 * The date is second precise.
 *
 * @param	date	Pointer to the MroDate variable where date is copied.
 *
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the last applied command date is copied in <i>date</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR		The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR			The value of the parameter <i>status</i> is NULL.
 *
 * @see	MroDate
 * @see	mro_getLastAppliedCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getLastAppliedCommandDate( 
	MroDate* date,
	int* status
	);



/*-----------------------------------------------------------------------------
 * Commands stock functions.
 */


/**
 * Inserts a command into the stock.
 * This function allows to insert a command into the stock. The command
 * is stored in the stock at the position specified by <i>index</i>. <br>
 * If a command has already been stored at <i>index</i> in the stock, it is
 * overwritten without warning.
 *
 * @param	command		Command to add to the command stock.
 *
 * @param	index		Index of the command stock where to put the command.
 *
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the command is added to the command stock,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_INVALID_COMMAND_ERROR		The set of values contained in <i>command</i> is invalid.
 * @throw	MRO_NULL_POINTER_ERROR			The parameter <i>command</i> is NULL.
 * @throw	MRO_OUT_OF_BOUNDS_ERROR			The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR		The device is not opened.
 *
 * @see	MroCommand
 * @see mro_getStockCommand
 * @see mro_isStockCommandDefined
 * @see mro_removeStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_setStockCommand( 
	MroCommand command, 
	int index,
	int* status
	);


/**
 * Retrieves a command from the stock.
 * This function allows to get a command stored into the command stock at the
 * position specified by <i>index</i>. <br/>
 * The command must have been stored in the command stock using 
 * mro_setStockCommand. 
 *
 * @param	command		Pointer to the array where to put the retrieved command.
 * @param	index		Index of the command stock of the command to retrieve.
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the command is retrieved from the command stock,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_OUT_OF_BOUNDS_ERROR			The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR		The mirao 52-e device is not opened.
 * @throw	MRO_UNDEFINED_VALUE_ERROR		The command specified by <i>index</i> is not defined in the stock.
 * @throw	MRO_NULL_POINTER_ERROR			The parameter <i>command</i> is NULL.
 *
 * @see MroCommand
 * @see mro_setStockCommand
 * @see mro_isStockCommandDefined
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getStockCommand( 
	MroCommand command,
	int index,
	int* status
	);


/**
 * Applies a command from the stock to the mirror.
 * The geometry of the mirror is modified according to the command stored in
 * the stock at <i>index</i>. <br>
 * The modification of the geometry is performed as quickly as possible.  <br>
 * The command must have been stored in the stock using mro_setStockCommand.
 *
 * @param	index	Index of the command stock of the command to apply.
 *
 * @param	trig	If MRO_TRUE, a hardware trig follow the command application.
 *
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the command is successfully sent to the mirror,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVICE_LOCKED_ERROR				The mirao 52-e device is locked.
 * @throw	MRO_OUT_OF_BOUNDS_ERROR				The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_UNDEFINED_VALUE_ERROR			The command specified by <i>index</i> is not defined in the stock.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao 52-e device has been detected.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The USB port is not opened.
 * @throw	MRO_USB_IO_ERROR					A communcation error occured on the USB port.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		System resources are insufficient to perform the operation.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 *
 * @see mro_setStockCommand
 * @see mro_applySmoothStockCommand
 * @see mro_applyCommand
 * @see mro_applySmoothCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_applyStockCommand(
	int index,
	MroBoolean trig,
	int* status
	);


/**
 * Applies a smooth command from the stock to the mirror.
 * The geometry of the mirror is modified according to the command stored in
 * the stock at <i>index</i>. <br>
 * With this function, the geometry of the mirror is modified without 
 * vibrations but taking a little more time than with <i>mro_applyStockCommand</i>. <br>
 * The command must have been stored in the stock using mro_setStockCommand.
 *
 * @param	index	Index of the command stock of the command to apply.
 *
 * @param	trig	If MRO_TRUE, a hardware trig follow the command application.
 *
 * @param	status		Pointer to an integer containing the error code if an
 *						error occurs or MRO_OK if the call returns
 *						successfully.
 *
 * @return	MRO_TRUE if the command is successfully sent to the mirror,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_DEVICE_LOCKED_ERROR				The mirao 52-e device is in protection mode.
 * @throw	MRO_OUT_OF_BOUNDS_ERROR				The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_UNDEFINED_VALUE_ERROR			The command specified by <i>index</i> is not defined in the stock.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao 52-e device has been detected.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The USB port is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error occured on the USB port.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		System resources are insufficient to perform the operation.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 *
 * @see mro_setStockCommand
 * @see mro_applyStockCommand
 * @see mro_applyCommand
 * @see mro_applySmoothStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_applySmoothStockCommand(
	int index,
	MroBoolean trig,
	int* status
	);


/**
 * Removes a command of the stock.
 * Deletes the command stored in the command stock at <i>index</i>. <br>
 * No warning if the command is not defined.
 *
 * @param	index	Command of the command stock to remove.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the command is successfully removed,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_OUT_OF_BOUNDS_ERROR			The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR		The device is not opened.
 *
 * @see	mro_setStockCommand
 * @see	mro_resetCommandStock
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_removeStockCommand(
	int index,
	int* status
	);


/**
 * Indicates if a stock contains a command at the specified index.
 * Return whether the command stored in the stock at <i>index</i> is defined
 * or not.
 * 
 * @param	index	Index of the command stock.
 *
 * @param	result	Pointer to a MroBoolean where to put the result.
 *					(MRO_TRUE if the command is defined, else MRO_FALSE)
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the result is put in <i>result</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_OUT_OF_BOUNDS_ERROR				The value of the parameter <i>index</i> is out of range.
 * @throw	MRO_NULL_POINTER_ERROR				The parameter <i>result</i> is NULL.
 *
 * @see MroBoolean
 * @see	mro_setStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_isStockCommandDefined(
	int index,
	MroBoolean* result,
	int* status
    );


/**
 * Clears the stock.
 * Removes all the command defined in the stock.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the command stock is emptied,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The device is not opened.
 *
 * @see mro_removeStockCommand
 * @see mro_setStockCommand
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_resetCommandStock(
	int* status
	);


/**
 * Indicates the number of commands in the stock.
 * Returns the number of commands defined in the stock.
 *
 * @param	size	Pointer to an integer to put the number of defined commands.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the number of defined commands is put in <i>size</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_NULL_POINTER_ERROR				The parameter <i>size</i> is NULL.
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The device is not opened.
 *
 * @see mro_setStockCommand
 * @see mro_getStockCommandMaxSize
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getCommandStockSize(
	int* size,
	int* status
	);


/**
 * Indicates the stock's capacity.
 * Returns the number of command that can contain the stock.
 *
 * @param	size	Pointer to the variable where to copy the command stock
 *					capacity.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the capacity of the command stock is copied in <i>size</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_NULL_POINTER_ERROR				The parameter <i>size</i> is NULL.
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The device is not opened.
 *
 * @see mro_getCommandStockSize
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getCommandStockMaxSize(
	int* size,
	int* status
	);



/*-----------------------------------------------------------------------------
 * Monitoring functions.
 */


/**
 * Indicates if the monitoring is enabled.
 * Returns whether the monitoring is enabled or not. <br>
 * At open, the monitoring is disabled. See mro_setMonitoringEnabled
 * for monitoring enabling.
 *
 * @param	enabled		Pointer of the MroBoolean where to put the result.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the result is put in <i>enabled</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR		The device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR			The parameter <i>enabled</i> is NULL.
 *
 * @see mro_setMonitoringEnabled
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_isMonitoringEnabled( 
	MroBoolean* enabled,
	int* status
	);


/**
 * Enables or disables the monitoring.
 * If <i>enabled</i> is true and the monitoring is disabled, the monitoring is 
 * started. <br>
 * If <i>enabled</i> is false and the monitoring is enabled, the monitoring is
 * stopped. <br>
 *
 * @remark	Enabling the monitoring allow:
 * - the use of the functions concerning the current temperature and intensity,
 * - enables the automatic reconnection on connection loss,
 * - enables the event notifications (see mro_registerCallback),
 * - enables the detection of connection problem and system locking.
 *
 * @param	enabled		If MRO_TRUE, the monitoring is enabled,
 *						if MRO_FALSE, the monitoring is disabled.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the monitoring is successfully enabled or disabled,
 *			MRO_FALSE an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_IO_ERROR					A communication error with the mirao 52-e device occured.
 * @throw	MRO_OPERATING_SYSTEM_ERROR			A system error occured while using an OS functionnality.
 * @throw	MRO_DEVICE_DRIVER_ERROR				An error occured using the USB driver.
 * @throw	MRO_USB_INVALID_HANDLE				The handle of the USB port is not more valid.
 * @throw	MRO_USB_DEVICE_NOT_OPENED			The USB port is not opened.
 * @throw	MRO_USB_IO_ERROR					A communication error occured on the USB device.
 * @throw	MRO_USB_INSUFFICIENT_RESOURCES		The system resources are insufficient to perform the operation.
 * @throw	MRO_USB_NOT_SUPPORTED				The function is not supported by the USB driver.
 *
 * @see MroInfo
 * @see	mro_isMonitoringEnabled
 * @see mro_registerCallback
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_setMonitoringEnabled( 
	MroBoolean enabled,
	int* status
	);


/**
 * Indicates the mirror temperature.
 * Returns the current mirror temperature in degree celsius (°C). <br>
 * The monitoring must be enabled.
 *
 * @remark	Warning: This function always returns an error as it is not 
 * implemented in this version of the mirao 52-e DLL.
 *
 * @param	val		Pointer to the MroTemperature where to put the mirror
 *					temperature.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the mirror temperature is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao mirao 52-e device has been detected.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 * 
 * @see MroTemperature
 * @see mro_setMonitoringEnabled
 * @see mro_getMirrorLockTemperature
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getMirrorTemperature(
	MroTemperature* val,
	int* status
	);


/**
 * Indicates the power supply temperature.
 * Returns the current temperature of the power supply. The temperature is 
 * indicated in degree celsuis (°C). <br>
 * The monitoring must be enabled.
 *
 * @param	val		Pointer to the MroTemperature where to put the power supply
 *					temperature.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the power supply temperature is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao 52-e device has been detected.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see MroTemperature
 * @see mro_setMonirotingEnabled
 * @see mro_getPowerSupplyLockTemperature
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getPowerSupplyTemperature(
	MroTemperature* val,
	int* status
	);


/**
 * Indicates the intensity in the negative coils.
 * Returns the intensity in the negative coils of the mirao 52-e device. <br>
 * The intensity is returned in Amperes (A). <br>
 * The monitoring must be enabled.
 * 
 * @param	val		Pointer of the MroIntensity where to put the intensity in
 *					the negative coils.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the negative coils intensity is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao device has been detected.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>status</i> is NULL.
 *
 * @see MroIntensity
 * @see mro_setMonitoringEnabled
 * @see mro_getNegativeCoilsIntensity
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getNegativeCoilsIntensity(
	MroIntensity* val,
	int* status
	);


/**
 * Indicates the intensity in the positive coils.
 * Returns the intensity in the positive coils. The intensity is returned in 
 * Amperes (A). <br>
 * The monitoring must be enabled.
 *
 * @param	val		Pointer of the MroIntensity where to put the intensity in
 *					the positive coils.
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the positive coils intensity is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao 52-e device has been detected.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see MroIntensity
 * @see mro_setMonitoringEnabled
 * @see mro_getPositiveCoilsLockIntensity
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getPositiveCoilsIntensity(
	MroIntensity* val,
	int* status
	);


/**
 * Indicates the mirror lock temperature.
 * Returns the temperature of the mirror over which the mirao 52-e is locked. <br>
 * The temperature is returned in degree Celsius (°C).
 *
 * @remark	Warning: this function always returns an error as it is not implemented in 
 * this version of the mirao 52-e DLL.
 *
 * @param	val		Pointer of the MroTemperature where to put the mirror
 *					lock temperature.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the mirror lock temperature is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see MroTemperature
 * @see mro_setMonitoringEnabled
 * @see mro_getMirrorTemperature
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getMirrorLockTemperature(
	MroTemperature* val,
	int* status
	);


/**
 * Indicates the power supply lock temperature.
 * Returns the power supply temperature over which the mirao 52-e device is locked. <br>
 * The temperature is returned in degree Celsius (°C).
 * 
 * @param	val		Pointer of the MroTemperature where to put the power supply
 *					lock temperature.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the power supply lock temperature is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see MroTemperature
 * @see mro_setMonitoringEnabled
 * @see mro_getPowerSupplyTemperature
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getPowerSupplyLockTemperature(
	MroTemperature* val,
	int* status
	);


/**
 * Indicates the negative coils lock intensity.
 * Returns the intensity in the negative coils over which mirao 52-e device is locked.<br>
 * The intensity is returned in Amperes (A).
 *
 * @param	val		Pointer of the MroIntensity where to put the negative coils
 *					lock intensity.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the negative coils lock intensity is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see	MroIntensity
 * @see mro_setMonitoringEnabled
 * @see mro_getNegativeCoilsIntensity
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getNegativeCoilsLockIntensity(
	MroIntensity* val,
	int* status
	);


/**
 * Indicates the positive coils lock intensity.
 * Returns the intensity in the positive coils over which the mirao 52-e device is locked. <br>
 * The intensity is returned in Amperes (A).
 *
 * @param	val		Pointer of the MroIntensity where to put the positive coils
 *					lock intensity.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the positive coils lock intensity is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see MroIntensity
 * @see mro_setMonitoringEnabled
 * @see mro_getPositiveCoilsIntensity
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_getPositiveCoilsLockIntensity(
	MroIntensity* val,
	int* status
	);


/**
 * Indicates if the device is locked.
 * Returns whether the mirao 52-e device is locked or not. <br>
 * The monitoring must be enabled.
 *
 * @param	val		Pointer to the MroBoolean where to put the result.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the result is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_DEVICE_DISCONNECTED_ERROR		A connection problem with the mirao 52-e device has been detected.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see mro_setMonitoringEnabled
 * @see mro_getMirrorLockTemperature
 * @see mro_getPowerSupplyLockTemperature
 * @see mro_getPositiveCoilsLockIntensity
 * @see mro_getNegativeCoilsLockIntensity
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_isLocked(
	MroBoolean* val,
	int* status
	);

/**
 * Indicates if the mirao 52-e is connected.
 * Returns False if a connection problem has been detected. <br>
 * The monitoring must be enabled.
 *
 * @param	val		Pointer to the MroBoolean where to put the result.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the result is put in <i>val</i>,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_UNAVAILABLE_DATA_ERROR			The monitoring is not enabled.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>val</i> is NULL.
 *
 * @see mro_setMonitoringEnabled
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_isConnected(
	MroBoolean* val,
	int* status
	 );

/**
 * Registers a function to call in case of event arrival.
 * The callback function pointed by <i>callback</i> will be notified of the
 * events concerning the mirao 52-e device. <br>
 * The notifications concern:
 * - transmission errors, 
 * - connection lost and recoverd,
 * - mirao lock entrance and exit,
 * - and monitoring start and stop
 * .
 * The <i>callback</i> function must respect this signature: <br>
 * - <code>void callbackFunctionName( MiraoInfo* miraoInfo );</code>
 * .
 * To be notified of these events (except for monitoring starting and stopping),
 * the monitoring must be enabled.
 *
 * @param	callback	Pointer to the callback function.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the callback is successfully registred,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>callback</i> is NULL.
 *
 * @see mro_setMonitoringEnabled
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_registerCallback(
	void (*callback)(MiraoInfo*),
	int* status
	);


/**
 * Unregisters the function to call in case of event arrival.
 * The callback function registered with <i>mro_registerCallback</i> is 
 * unregistered. It is not notificated of events about the mirao 52-e device
 * anymore. <br>
 * If no callback function is registered, nothing happen.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 *
 * @return	MRO_TRUE if the callback is successfully unregistred,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The device is not opened.
 *
 * @see mro_registerCallback
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_unregisterCallback(
	int* status
	);



/*-----------------------------------------------------------------------------
 * MRO files manipulation functions
 */


/**
 * Saves a command to a file.
 * The set of values contained in <i>command</i> is written into the file
 * specified by <i>filePath</i>. <br>
 * The output file has the MRO format version MRO.001.001.20080609. Its name
 * must end with the extension <code>.mro</code> .
 *
 * @param	command		Command to save.
 *
 * @param	filaPath	Null terminated character string containing the path of
 *						the file to create.
 *
 * @param	overwrite	If MRO_TRUE, if the file already exists it is overwritten,
 *						if MRO_FALSE, if the file already exists an error is
 *						raised.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 * 
 * @return	MRO_TRUE if the command is successfully saved into the specified file,
 *			MRO_TRUE if an error occurs.
 *
 * @throw	MRO_DEVICE_NOT_OPENED_ERROR			The mirao 52-e device is not opened.
 * @throw	MRO_INVALID_COMMAND_ERROR			The set of values contained in <i>command</i> is invalid.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>filePath</i> is NULL.
 * @throw	MRO_FILE_EXISTS_ERROR				The file specified by <i>filePath</i> already exists and the parameter <i>overwrite</i> is set to MRO_FALSE.
 * @throw	MRO_OUT_OF_SPECIFICATIONS_ERROR		The value of the parameter <i>filePath</i> is out of specifications. It must be a file name ending by .mro.
 * @throw	MRO_FILE_IO_ERROR					An error occured while writing the file.
 * @throw	MRO_FILE_IO_EACCES					Permission on the file denied.
 * @throw	MRO_FILE_IO_EAGAIN					No more free processes.
 * @throw	MRO_FILE_IO_EBADF					Bad file descriptor.
 * @throw	MRO_FILE_IO_EINVAL					Invalid argument passed to the write function.
 * @throw	MRO_FILE_IO_EMFILE					Too many open files.
 * @throw	MRO_FILE_IO_ENOENT					No such file or directory.
 * @throw	MRO_FILE_IO_ENOMEM					Not enough memory in the system.
 * @throw	MRO_FILE_IO_ENOSPC					No more sapce available on the device.
 *
 * @see MroCommand
 * @see mro_readCommandFile
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_writeCommandFile( 
	MroCommand command, 
	char* filePath, 
	MroBoolean overwrite,
	int* status
	);


/**
 * Reads a command from a file.
 * The set of values contained in the file specified by <i>filePath</i> is
 * stored into <i>command</i>. <br>
 * The file must be a valid MRO.001.001.20080609 file with the extension 
 * <code>.mro</code>.
 *
 * @param	filePath	Null terminated character string containing the path of
 *						the file to create.
 *
 * @param	command		Array into which to put the command read.
 *
 * @param	status	Pointer to an integer containing the error code if an error
 *					occurs or MRO_OK if the call returns successfully.
 * 
 * @return	MRO_TRUE if the command is successfully read,
 *			MRO_FALSE if an error occurs.
 *
 * @throw	MRO_INVALID_COMMAND_ERROR			The set of values contained in <i>command</i> is invalid.
 * @throw	MRO_NULL_POINTER_ERROR				The value of the parameter <i>filePath</i> or <i>command</i> is NULL.
 * @throw	MRO_OUT_OF_SPECIFICATIONS_ERROR		The value of the parameter <i>filePath</i> is out of specifications. It must be a filename ending by .mro.
 * @throw	MRO_FILE_FORMAT_ERROR				The file specified by <i>filePath</i> has not a valid MRO file format.
 * @throw	MRO_FILE_FORMAT_VERSION_ERROR		The version of the MRO file format is not supported.
 * @throw	MRO_FILE_IO_ERROR					An error occurd while reading the file.
 * @throw	MRO_FILE_IO_EACCES					Permission denied on the file.
 * @throw	MRO_FILE_IO_EAGAIN					No more free processes.
 * @throw	MRO_FILE_IO_EBADF					Bad file descriptor.
 * @throw	MRO_FILE_IO_EINVAL					Invalid argument passed to the read function.
 * @throw	MRO_FILE_IO_EMFILE					Too many open files.
 * @throw	MRO_FILE_IO_ENOENT					No such file or directory.
 * @throw	MRO_FILE_IO_ENOMEM					Not enough free memory in the system.
 * @throw	MRO_FILE_IO_ENOSPC					No more space available on the device.
 *
 * @see MroCommand
 * @see mro_writeCommandFile
 */
MIRAOEXPORT MroBoolean MIRAOCALL mro_readCommandFile(
	char* filePath,
	MroCommand command,
	int* status
	);



#ifdef __cplusplus
}
#endif
#endif


