
from pycket import impersonators as imp
from pycket import values
from pycket import values_struct
from pycket import values_hash
from pycket.error import SchemeException
from pycket.prims.expose import expose, expose_val
from pycket.prims.equal import equal_func, EqualInfo
from rpython.rlib import jit

expose_val("impersonator-prop:application-mark", imp.w_impersonator_prop_application_mark)

# Used to find the first impersonator-property
@jit.unroll_safe
def find_prop_start_index(args):
    for i, v in enumerate(args):
        if isinstance(v, imp.W_ImpPropertyDescriptor):
            return i
    return len(args)

@jit.unroll_safe
def unpack_properties(args, name):
    idx = find_prop_start_index(args)
    args, props = args[:idx], args[idx:]
    prop_len = len(props)

    if prop_len % 2 != 0:
        raise SchemeException(name + ": not all properties have corresponding values")

    prop_keys = [props[i] for i in range(0, prop_len, 2)]
    prop_vals = [props[i] for i in range(1, prop_len, 2)]

    for k in prop_keys:
        if not isinstance(k, imp.W_ImpPropertyDescriptor):
            desc = "%s: %s is not a property descriptor" % (name, k.tostring())
            raise SchemeException(desc)

    return args, prop_keys, prop_vals

def unpack_vector_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 3:
        raise SchemeException(name + ": not given 3 required arguments")
    v, refh, seth = args
    if not isinstance(v, values.W_MVector):
        raise SchemeException(name + ": first arg not a vector")
    if not refh.iscallable() or not seth.iscallable:
        raise SchemeException(name + ": provided handler is not callable")

    return v, refh, seth, prop_keys, prop_vals

def unpack_procedure_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 2:
        raise SchemeException(name + ": not given 2 required arguments")
    proc, check = args
    if not proc.iscallable():
        raise SchemeException(name + ": first argument is not a procedure")
    if not check.iscallable():
        raise SchemeException(name + ": handler is not a procedure")
    return proc, check, prop_keys, prop_vals

def unpack_box_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 3:
        raise SchemeException(name + ": not given three required arguments")
    box, unboxh, seth = args
    if not unboxh.iscallable():
        raise SchemeException(name + ": supplied unbox handler is not callable")
    if not seth.iscallable():
        raise SchemeException(name + ": supplied set-box! handler is not callable")
    return box, unboxh, seth, prop_keys, prop_vals

def unpack_cmk_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    if len(args) != 3:
        raise SchemeException(name + ": not give three required arguments")
    key, get, set = args
    if not isinstance(key, values.W_ContinuationMarkKey):
        raise SchemeException(name + ": supplied key is not a continuation-mark-key")
    if not get.iscallable():
        raise SchemeException(name + ": supplied get-proc is not callable")
    if not set.iscallable():
        raise SchemeException(name + ": supplied set-proc is not callable")
    return key, get, set, prop_keys, prop_vals

def unpack_hash_args(args, name):
    args, prop_keys, prop_vals = unpack_properties(args, name)
    clear_proc = values.w_false
    if len(args) == 5:
        hash, ref_proc, set_proc, remove_proc, key_proc = args
    elif len(args) == 6:
        hash, ref_proc, set_proc, remove_proc, key_proc, clear_proc = args
    else:
        raise SchemeException(name + ": wrong number of arguments")
    if not isinstance(hash, values_hash.W_HashTable):
        raise SchemeException(name + ": first argument is not a hash")
    if not ref_proc.iscallable():
        raise SchemeException(name + ": ref-proc is not callable")
    if not set_proc.iscallable():
        raise SchemeException(name + ": set-proc is not callable")
    if not remove_proc.iscallable():
        raise SchemeException(name + ": remove-proc is not callable")
    if not key_proc.iscallable():
        raise SchemeException(name + ": key-proc is not callable")
    if clear_proc is not values.w_false and not clear_proc.iscallable():
        raise SchemeException(name + ": clear-proc is not callable")
    return hash, ref_proc, set_proc, remove_proc, key_proc, clear_proc, prop_keys, prop_vals

@expose("impersonate-hash")
def impersonate_hash(args):
    unpacked = unpack_hash_args(args, "impersonate-hash")
    if unpacked[0].immutable():
        raise SchemeException("impersonate-hash: cannot impersonate immutable hash")
    return imp.W_ImpHashTable(*unpacked)

@expose("chaperone-hash")
def chaperone_hash(args):
    unpacked = unpack_hash_args(args, "chaperone-hash")
    return imp.W_ImpHashTable(*unpacked)

@expose("impersonate-procedure")
def impersonate_procedure(args):
    unpacked = unpack_procedure_args(args, "impersonate-procedure")
    return imp.W_ImpProcedure(*unpacked)

@expose("chaperone-procedure")
def chaperone_procedure(args):
    unpacked = unpack_procedure_args(args, "chaperone-procedure")
    return imp.W_ChpProcedure(*unpacked)

@expose("impersonate-vector")
def impersonate_vector(args):
    unpacked = unpack_vector_args(args, "impersonate-vector")
    if unpacked[0].immutable():
        raise SchemeException("impersonate-vector: cannot impersonate immutable vector")
    return imp.W_ImpVector(*unpacked)

@expose("chaperone-vector")
def chaperone_vector(args):
    unpacked = unpack_vector_args(args, "chaperone-vector")
    return imp.W_ChpVector(*unpacked)

# Need to check that fields are mutable
@expose("impersonate-struct")
@jit.unroll_safe
def impersonate_struct(args):
    args, prop_keys, prop_vals = unpack_properties(args, "impersonate-struct")
    if len(args) < 1 or len(args) % 2 != 1:
        raise SchemeException("impersonate-struct: arity mismatch")
    if len(args) == 1:
        return args[0]

    struct, args = args[0], args[1:]

    if not isinstance(struct, values_struct.W_RootStruct):
        raise SchemeException("impersonate-struct: not given struct")

    struct_type = struct.struct_type()
    assert isinstance(struct_type, values_struct.W_StructType)

    # Consider storing immutables in an easier form in the structs implementation
    immutables = struct_type.immutables

    # Slicing would be nicer
    overrides = [args[i] for i in range(0, len(args), 2)]
    handlers  = [args[i] for i in range(1, len(args), 2)]

    for i in overrides:
        if not imp.valid_struct_proc(i):
            raise SchemeException("impersonate-struct: not given valid field accessor")
        elif (isinstance(i, values_struct.W_StructFieldMutator) and
                i.field in immutables):
            raise SchemeException("impersonate-struct: cannot impersonate immutable field")
        elif (isinstance(i, values_struct.W_StructFieldAccessor) and
                i.field in immutables):
            raise SchemeException("impersonate-struct: cannot impersonate immutable field")

    for i in handlers:
        if not i.iscallable():
            raise SchemeException("impersonate-struct: supplied hander is not a procedure")

    return imp.W_ImpStruct(struct, overrides, handlers, prop_keys, prop_vals)

@expose("chaperone-struct")
@jit.unroll_safe
def chaperone_struct(args):
    args, prop_keys, prop_vals = unpack_properties(args, "chaperone-struct")
    if len(args) < 1 or len(args) % 2 != 1:
        raise SchemeException("chaperone-struct: arity mismatch")
    if len(args) == 1:
        return args[0]

    struct, args = args[0], args[1:]

    if not isinstance(struct, values_struct.W_RootStruct):
        raise SchemeException("chaperone-struct: not given struct")

    # Slicing would be nicer
    overrides = [args[i] for i in range(0, len(args), 2)]
    handlers  = [args[i] for i in range(1, len(args), 2)]

    for i in overrides:
        if not imp.valid_struct_proc(i):
            raise SchemeException("chaperone-struct: not given valid field accessor")

    for i in handlers:
        if not i.iscallable():
            raise SchemeException("chaperone-struct: supplied hander is not a procedure")

    return imp.W_ChpStruct(struct, overrides, handlers, prop_keys, prop_vals)

@expose("chaperone-box")
def chaperone_box(args):
    unpacked = unpack_box_args(args, "chaperone-box")
    return imp.W_ChpBox(*unpacked)

@expose("impersonate-box")
def impersonate_box(args):
    unpacked = unpack_box_args(args, "impersonate-box")
    if unpacked[0].immutable():
        raise SchemeException("Cannot impersonate immutable box")
    return imp.W_ImpBox(*unpacked)

@expose("chaperone-continuation-mark-key")
def ccmk(args):
    unpacked = unpack_cmk_args(args, "chaperone-continuation-mark-key")
    return imp.W_ChpContinuationMarkKey(*unpacked)

@expose("impersonate-continuation-mark-key")
def icmk(args):
    unpacked = unpack_cmk_args(args, "impersonate-continuation-mark-key")
    return imp.W_ImpContinuationMarkKey(*unpacked)

@expose("chaperone-of?", [values.W_Object, values.W_Object], simple=False)
def chaperone_of(a, b, env, cont):
    info = EqualInfo.CHAPERONE_SINGLETON
    return equal_func(a, b, info, env, cont)

@expose("impersonator-of?", [values.W_Object, values.W_Object], simple=False)
def impersonator_of(a, b, env, cont):
    info = EqualInfo.IMPERSONATOR_SINGLETON
    return equal_func(a, b, info, env, cont)

@expose("impersonator?", [values.W_Object])
def impersonator(x):
    return values.W_Bool.make(x.is_impersonator())

@expose("chaperone?", [values.W_Object])
def chaperone(x):
    return values.W_Bool.make(x.is_chaperone())

@expose("make-impersonator-property", [values.W_Symbol], simple=False)
def make_imp_prop(sym, env, cont):
    from pycket.interpreter import return_multi_vals
    name = sym.utf8value
    prop = imp.W_ImpPropertyDescriptor(name)
    pred = imp.W_ImpPropertyPredicate(prop)
    accs = imp.W_ImpPropertyAccessor(prop)
    return return_multi_vals(values.Values.make([prop, pred, accs]), env, cont)

